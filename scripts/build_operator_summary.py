from __future__ import annotations

import argparse
from datetime import datetime
from datetime import timezone
from html import escape
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.ledger import get_job_by_id  # noqa: E402
from orchestrator.ledger import get_latest_job  # noqa: E402
from orchestrator.ledger import get_rollback_execution_by_job_id  # noqa: E402
from orchestrator.ledger import get_rollback_trace_by_job_id  # noqa: E402
from orchestrator.ledger import record_machine_review_payload_path  # noqa: E402
from automation.review.recovery_policy import POLICY_VERSION  # noqa: E402
from automation.review.recovery_policy import evaluate_recovery_policy  # noqa: E402
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface  # noqa: E402
from automation.orchestration.operator_explainability import build_operator_explainability_surface  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build operator summary artifacts for a recorded job")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--job-id")
    selector.add_argument("--latest", action="store_true")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
    parser.add_argument("--out-dir")
    return parser


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return None


def _read_json(path_value: Any) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _extract_decision_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "decision": None,
            "rule_id": None,
            "recommended_next_action": None,
            "blocking_reasons": [],
            "readiness_status": None,
            "readiness_next_action": None,
            "automation_eligible": None,
            "manual_intervention_required": None,
            "unresolved_blockers": [],
            "prerequisites_satisfied": None,
        }
    return {
        "decision": payload.get("decision"),
        "rule_id": payload.get("rule_id"),
        "recommended_next_action": payload.get("recommended_next_action"),
        "blocking_reasons": (
            [str(item) for item in payload.get("blocking_reasons", [])]
            if isinstance(payload.get("blocking_reasons"), (list, tuple))
            else []
        ),
        "readiness_status": payload.get("readiness_status"),
        "readiness_next_action": payload.get("readiness_next_action"),
        "automation_eligible": payload.get("automation_eligible"),
        "manual_intervention_required": payload.get("manual_intervention_required"),
        "unresolved_blockers": (
            [str(item) for item in payload.get("unresolved_blockers", [])]
            if isinstance(payload.get("unresolved_blockers"), (list, tuple))
            else []
        ),
        "prerequisites_satisfied": payload.get("prerequisites_satisfied"),
    }


def _extract_checkpoint_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "checkpoint_stage": None,
            "decision": None,
            "rule_id": None,
            "recommended_next_action": None,
            "manual_intervention_required": None,
            "global_stop_recommended": None,
            "blocking_reasons": [],
        }
    return {
        "checkpoint_stage": payload.get("checkpoint_stage"),
        "decision": payload.get("decision"),
        "rule_id": payload.get("rule_id"),
        "recommended_next_action": payload.get("recommended_next_action"),
        "manual_intervention_required": payload.get("manual_intervention_required"),
        "global_stop_recommended": payload.get("global_stop_recommended"),
        "blocking_reasons": (
            [str(item) for item in payload.get("blocking_reasons", [])]
            if isinstance(payload.get("blocking_reasons"), (list, tuple))
            else []
        ),
    }


def _extract_execution_receipt_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "execution_type": None,
            "rollback_mode": None,
            "status": None,
            "summary": None,
            "started_at": None,
            "finished_at": None,
            "trigger_reason": None,
            "branch_name": None,
            "remote_name": None,
            "base_branch": None,
            "head_branch": None,
            "pr_number": None,
            "pr_url": None,
            "commit_sha": None,
            "merge_commit_sha": None,
            "resulting_commit_sha": None,
            "resulting_pr_state": None,
            "resulting_branch_state": None,
            "failure_reason": None,
            "manual_intervention_required": None,
            "replan_required": None,
            "automatic_continuation_blocked": None,
            "blocking_reasons": [],
            "attempted": None,
            "execution_allowed": None,
            "execution_authority_status": None,
            "validation_status": None,
            "execution_gate_status": None,
            "authority_blocked_reason": None,
            "validation_blocked_reason": None,
            "authority_blocked_reasons": [],
            "validation_blocked_reasons": [],
            "missing_prerequisites": [],
            "missing_required_refs": [],
            "unsafe_repo_state": [],
            "remote_pr_ambiguity": [],
            "remote_github_status": None,
            "remote_github_blocked": None,
            "remote_github_blocked_reason": None,
            "remote_github_blocked_reasons": [],
            "remote_github_missing_or_ambiguous": None,
            "remote_state_status": None,
            "remote_state_blocked": None,
            "remote_state_blocked_reason": None,
            "remote_state_missing_or_ambiguous": None,
            "upstream_tracking_status": None,
            "remote_divergence_status": None,
            "remote_branch_status": None,
            "existing_pr_status": None,
            "pr_creation_state_status": None,
            "pr_duplication_risk": None,
            "mergeability_status": None,
            "merge_requirements_status": None,
            "required_checks_status": None,
            "review_state_status": None,
            "branch_protection_status": None,
            "github_state_status": None,
            "github_state_unavailable": None,
            "manual_approval_required": None,
            "rollback_aftermath_status": None,
            "rollback_aftermath_blocked": None,
            "rollback_aftermath_blocked_reason": None,
            "rollback_aftermath_blocked_reasons": [],
            "rollback_aftermath_missing_or_ambiguous": None,
            "rollback_validation_status": None,
            "rollback_manual_followup_required": None,
            "rollback_remote_followup_required": None,
            "rollback_conflict_status": None,
            "rollback_remote_state_status": None,
            "rollback_divergence_status": None,
            "rollback_pr_state_status": None,
            "rollback_branch_state_status": None,
            "rollback_repo_cleanliness_status": None,
            "rollback_head_state_status": None,
            "rollback_revert_commit_status": None,
            "rollback_post_validation_status": None,
            "rollback_remote_github_status": None,
        }
    return {
        "execution_type": payload.get("execution_type"),
        "rollback_mode": payload.get("rollback_mode"),
        "status": payload.get("status"),
        "summary": payload.get("summary"),
        "started_at": payload.get("started_at"),
        "finished_at": payload.get("finished_at"),
        "trigger_reason": payload.get("trigger_reason"),
        "branch_name": payload.get("branch_name"),
        "remote_name": payload.get("remote_name"),
        "base_branch": payload.get("base_branch"),
        "head_branch": payload.get("head_branch"),
        "pr_number": payload.get("pr_number"),
        "pr_url": payload.get("pr_url"),
        "commit_sha": payload.get("commit_sha"),
        "merge_commit_sha": payload.get("merge_commit_sha"),
        "resulting_commit_sha": payload.get("resulting_commit_sha"),
        "resulting_pr_state": payload.get("resulting_pr_state"),
        "resulting_branch_state": (
            dict(payload.get("resulting_branch_state"))
            if isinstance(payload.get("resulting_branch_state"), dict)
            else None
        ),
        "failure_reason": payload.get("failure_reason"),
        "manual_intervention_required": payload.get("manual_intervention_required"),
        "replan_required": payload.get("replan_required"),
        "automatic_continuation_blocked": payload.get("automatic_continuation_blocked"),
        "blocking_reasons": (
            [str(item) for item in payload.get("blocking_reasons", [])]
            if isinstance(payload.get("blocking_reasons"), (list, tuple))
            else []
        ),
        "attempted": payload.get("attempted"),
        "execution_allowed": payload.get("execution_allowed"),
        "execution_authority_status": payload.get("execution_authority_status"),
        "validation_status": payload.get("validation_status"),
        "execution_gate_status": payload.get("execution_gate_status"),
        "authority_blocked_reason": payload.get("authority_blocked_reason"),
        "validation_blocked_reason": payload.get("validation_blocked_reason"),
        "authority_blocked_reasons": (
            [str(item) for item in payload.get("authority_blocked_reasons", [])]
            if isinstance(payload.get("authority_blocked_reasons"), (list, tuple))
            else []
        ),
        "validation_blocked_reasons": (
            [str(item) for item in payload.get("validation_blocked_reasons", [])]
            if isinstance(payload.get("validation_blocked_reasons"), (list, tuple))
            else []
        ),
        "missing_prerequisites": (
            [str(item) for item in payload.get("missing_prerequisites", [])]
            if isinstance(payload.get("missing_prerequisites"), (list, tuple))
            else []
        ),
        "missing_required_refs": (
            [str(item) for item in payload.get("missing_required_refs", [])]
            if isinstance(payload.get("missing_required_refs"), (list, tuple))
            else []
        ),
        "unsafe_repo_state": (
            [str(item) for item in payload.get("unsafe_repo_state", [])]
            if isinstance(payload.get("unsafe_repo_state"), (list, tuple))
            else []
        ),
        "remote_pr_ambiguity": (
            [str(item) for item in payload.get("remote_pr_ambiguity", [])]
            if isinstance(payload.get("remote_pr_ambiguity"), (list, tuple))
            else []
        ),
        "remote_github_status": payload.get("remote_github_status"),
        "remote_github_blocked": payload.get("remote_github_blocked"),
        "remote_github_blocked_reason": payload.get("remote_github_blocked_reason"),
        "remote_github_blocked_reasons": (
            [str(item) for item in payload.get("remote_github_blocked_reasons", [])]
            if isinstance(payload.get("remote_github_blocked_reasons"), (list, tuple))
            else []
        ),
        "remote_github_missing_or_ambiguous": payload.get("remote_github_missing_or_ambiguous"),
        "remote_state_status": payload.get("remote_state_status"),
        "remote_state_blocked": payload.get("remote_state_blocked"),
        "remote_state_blocked_reason": payload.get("remote_state_blocked_reason"),
        "remote_state_missing_or_ambiguous": payload.get("remote_state_missing_or_ambiguous"),
        "upstream_tracking_status": payload.get("upstream_tracking_status"),
        "remote_divergence_status": payload.get("remote_divergence_status"),
        "remote_branch_status": payload.get("remote_branch_status"),
        "existing_pr_status": payload.get("existing_pr_status"),
        "pr_creation_state_status": payload.get("pr_creation_state_status"),
        "pr_duplication_risk": payload.get("pr_duplication_risk"),
        "mergeability_status": payload.get("mergeability_status"),
        "merge_requirements_status": payload.get("merge_requirements_status"),
        "required_checks_status": payload.get("required_checks_status"),
        "review_state_status": payload.get("review_state_status"),
        "branch_protection_status": payload.get("branch_protection_status"),
        "github_state_status": payload.get("github_state_status"),
        "github_state_unavailable": payload.get("github_state_unavailable"),
        "manual_approval_required": payload.get("manual_approval_required"),
        "rollback_aftermath_status": payload.get("rollback_aftermath_status"),
        "rollback_aftermath_blocked": payload.get("rollback_aftermath_blocked"),
        "rollback_aftermath_blocked_reason": payload.get("rollback_aftermath_blocked_reason"),
        "rollback_aftermath_blocked_reasons": (
            [str(item) for item in payload.get("rollback_aftermath_blocked_reasons", [])]
            if isinstance(payload.get("rollback_aftermath_blocked_reasons"), (list, tuple))
            else []
        ),
        "rollback_aftermath_missing_or_ambiguous": payload.get("rollback_aftermath_missing_or_ambiguous"),
        "rollback_validation_status": payload.get("rollback_validation_status"),
        "rollback_manual_followup_required": payload.get("rollback_manual_followup_required"),
        "rollback_remote_followup_required": payload.get("rollback_remote_followup_required"),
        "rollback_conflict_status": payload.get("rollback_conflict_status"),
        "rollback_remote_state_status": payload.get("rollback_remote_state_status"),
        "rollback_divergence_status": payload.get("rollback_divergence_status"),
        "rollback_pr_state_status": payload.get("rollback_pr_state_status"),
        "rollback_branch_state_status": payload.get("rollback_branch_state_status"),
        "rollback_repo_cleanliness_status": payload.get("rollback_repo_cleanliness_status"),
        "rollback_head_state_status": payload.get("rollback_head_state_status"),
        "rollback_revert_commit_status": payload.get("rollback_revert_commit_status"),
        "rollback_post_validation_status": payload.get("rollback_post_validation_status"),
        "rollback_remote_github_status": payload.get("rollback_remote_github_status"),
    }


def _with_operator_explainability(run_state: dict[str, Any]) -> dict[str, Any]:
    lifecycle_surface = build_lifecycle_terminal_state_surface(run_state)
    merged = {**run_state, **lifecycle_surface}
    return {
        **merged,
        **build_operator_explainability_surface(
            merged,
            include_rendering_details=True,
        ),
    }


def _read_lifecycle_artifacts(result_path_value: Any) -> dict[str, Any]:
    result_path = Path(str(result_path_value).strip()) if isinstance(result_path_value, str) else None
    if result_path is None or not result_path.exists():
        return {
            "paths": {
                "checkpoint_decision": None,
                "commit_decision": None,
                "merge_decision": None,
                "rollback_decision": None,
                "commit_execution": None,
                "push_execution": None,
                "pr_execution": None,
                "merge_execution": None,
                "rollback_execution": None,
                "run_state": None,
            },
            "checkpoint_decision": _extract_checkpoint_summary(None),
            "commit_decision": _extract_decision_summary(None),
            "merge_decision": _extract_decision_summary(None),
            "rollback_decision": _extract_decision_summary(None),
            "commit_execution": _extract_execution_receipt_summary(None),
            "push_execution": _extract_execution_receipt_summary(None),
            "pr_execution": _extract_execution_receipt_summary(None),
            "merge_execution": _extract_execution_receipt_summary(None),
            "rollback_execution": _extract_execution_receipt_summary(None),
            "run_state": _with_operator_explainability({
                "state": None,
                "orchestration_state": None,
                "global_stop": None,
                "global_stop_reason": None,
                "continue_allowed": None,
                "run_paused": None,
                "manual_intervention_required": None,
                "rollback_evaluation_pending": None,
                "global_stop_recommended": None,
                "next_run_action": None,
                "loop_state": None,
                "next_safe_action": None,
                "loop_blocked_reason": None,
                "loop_blocked_reasons": [],
                "resumable": None,
                "terminal": None,
                "loop_manual_intervention_required": None,
                "loop_replan_required": None,
                "rollback_completed": None,
                "delivery_completed": None,
                "loop_allowed_actions": [],
                "unit_blocked": None,
                "readiness_summary": {},
                "readiness_blocked": None,
                "readiness_manual_required": None,
                "readiness_awaiting_prerequisites": None,
                "push_execution_summary": {},
                "pr_execution_summary": {},
                "merge_execution_summary": {},
                "push_execution_succeeded": None,
                "pr_execution_succeeded": None,
                "merge_execution_succeeded": None,
                "push_execution_pending": None,
                "pr_execution_pending": None,
                "merge_execution_pending": None,
                "push_execution_failed": None,
                "pr_execution_failed": None,
                "merge_execution_failed": None,
                "delivery_execution_manual_intervention_required": None,
                "rollback_execution_summary": {},
                "rollback_execution_attempted": None,
                "rollback_execution_succeeded": None,
                "rollback_execution_pending": None,
                "rollback_execution_failed": None,
                "rollback_execution_manual_intervention_required": None,
                "rollback_replan_required": None,
                "rollback_automatic_continuation_blocked": None,
                "rollback_aftermath_summary": {},
                "rollback_aftermath_status": None,
                "rollback_aftermath_blocked": None,
                "rollback_aftermath_manual_required": None,
                "rollback_aftermath_missing_or_ambiguous": None,
                "rollback_aftermath_blocked_reason": None,
                "rollback_aftermath_blocked_reasons": [],
                "rollback_remote_followup_required": None,
                "rollback_manual_followup_required": None,
                "rollback_validation_failed": None,
                "authority_validation_summary": {},
                "authority_validation_blocked": None,
                "execution_authority_blocked": None,
                "validation_blocked": None,
                "authority_validation_manual_required": None,
                "authority_validation_missing_or_ambiguous": None,
                "authority_validation_blocked_reason": None,
                "authority_validation_blocked_reasons": [],
                "remote_github_summary": {},
                "remote_github_blocked": None,
                "remote_github_manual_required": None,
                "remote_github_missing_or_ambiguous": None,
                "remote_github_blocked_reason": None,
                "remote_github_blocked_reasons": [],
                "policy_status": None,
                "policy_blocked": None,
                "policy_manual_required": None,
                "policy_replan_required": None,
                "policy_resume_allowed": None,
                "policy_terminal": None,
                "policy_blocked_reason": None,
                "policy_blocked_reasons": [],
                "policy_primary_blocker_class": None,
                "policy_primary_action": None,
                "policy_allowed_actions": [],
                "policy_disallowed_actions": [],
                "policy_manual_actions": [],
                "policy_resumable_reason": None,
                "lifecycle_closure_status": None,
                "lifecycle_safely_closed": None,
                "lifecycle_terminal": None,
                "lifecycle_resumable": None,
                "lifecycle_manual_required": None,
                "lifecycle_replan_required": None,
                "lifecycle_execution_complete_not_closed": None,
                "lifecycle_rollback_complete_not_closed": None,
                "lifecycle_blocked_reason": None,
                "lifecycle_blocked_reasons": [],
                "lifecycle_primary_closure_issue": None,
                "lifecycle_stop_class": None,
            }),
        }

    unit_dir = result_path.parent
    run_root = unit_dir.parent
    checkpoint_path = unit_dir / "checkpoint_decision.json"
    commit_path = unit_dir / "commit_decision.json"
    merge_path = unit_dir / "merge_decision.json"
    rollback_path = unit_dir / "rollback_decision.json"
    commit_execution_path = unit_dir / "commit_execution.json"
    push_execution_path = unit_dir / "push_execution.json"
    pr_execution_path = unit_dir / "pr_execution.json"
    merge_execution_path = unit_dir / "merge_execution.json"
    rollback_execution_path = unit_dir / "rollback_execution.json"
    run_state_path = run_root / "run_state.json"

    checkpoint_payload = _read_json(str(checkpoint_path))
    commit_payload = _read_json(str(commit_path))
    merge_payload = _read_json(str(merge_path))
    rollback_payload = _read_json(str(rollback_path))
    commit_execution_payload = _read_json(str(commit_execution_path))
    push_execution_payload = _read_json(str(push_execution_path))
    pr_execution_payload = _read_json(str(pr_execution_path))
    merge_execution_payload = _read_json(str(merge_execution_path))
    rollback_execution_payload = _read_json(str(rollback_execution_path))
    run_state_payload = _read_json(str(run_state_path))

    return {
        "paths": {
            "checkpoint_decision": str(checkpoint_path) if checkpoint_path.exists() else None,
            "commit_decision": str(commit_path) if commit_path.exists() else None,
            "merge_decision": str(merge_path) if merge_path.exists() else None,
            "rollback_decision": str(rollback_path) if rollback_path.exists() else None,
            "commit_execution": str(commit_execution_path) if commit_execution_path.exists() else None,
            "push_execution": str(push_execution_path) if push_execution_path.exists() else None,
            "pr_execution": str(pr_execution_path) if pr_execution_path.exists() else None,
            "merge_execution": str(merge_execution_path) if merge_execution_path.exists() else None,
            "rollback_execution": str(rollback_execution_path) if rollback_execution_path.exists() else None,
            "run_state": str(run_state_path) if run_state_path.exists() else None,
        },
        "checkpoint_decision": _extract_checkpoint_summary(checkpoint_payload),
        "commit_decision": _extract_decision_summary(commit_payload),
        "merge_decision": _extract_decision_summary(merge_payload),
        "rollback_decision": _extract_decision_summary(rollback_payload),
        "commit_execution": _extract_execution_receipt_summary(commit_execution_payload),
        "push_execution": _extract_execution_receipt_summary(push_execution_payload),
        "pr_execution": _extract_execution_receipt_summary(pr_execution_payload),
        "merge_execution": _extract_execution_receipt_summary(merge_execution_payload),
        "rollback_execution": _extract_execution_receipt_summary(rollback_execution_payload),
        "run_state": _with_operator_explainability({
            "state": (
                run_state_payload.get("state")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "orchestration_state": (
                run_state_payload.get("orchestration_state")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "global_stop": (
                run_state_payload.get("global_stop")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "global_stop_reason": (
                run_state_payload.get("global_stop_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "continue_allowed": (
                run_state_payload.get("continue_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "run_paused": (
                run_state_payload.get("run_paused")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "manual_intervention_required": (
                run_state_payload.get("manual_intervention_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_evaluation_pending": (
                run_state_payload.get("rollback_evaluation_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "global_stop_recommended": (
                run_state_payload.get("global_stop_recommended")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "next_run_action": (
                run_state_payload.get("next_run_action")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_state": (
                run_state_payload.get("loop_state")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "next_safe_action": (
                run_state_payload.get("next_safe_action")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_blocked_reason": (
                run_state_payload.get("loop_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_blocked_reasons": (
                [str(item) for item in run_state_payload.get("loop_blocked_reasons", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("loop_blocked_reasons"), (list, tuple))
                else []
            ),
            "resumable": (
                run_state_payload.get("resumable")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "terminal": (
                run_state_payload.get("terminal")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_manual_intervention_required": (
                run_state_payload.get("loop_manual_intervention_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_replan_required": (
                run_state_payload.get("loop_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_completed": (
                run_state_payload.get("rollback_completed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "delivery_completed": (
                run_state_payload.get("delivery_completed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_allowed_actions": (
                [str(item) for item in run_state_payload.get("loop_allowed_actions", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("loop_allowed_actions"), (list, tuple))
                else []
            ),
            "unit_blocked": (
                run_state_payload.get("unit_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "readiness_summary": (
                dict(run_state_payload.get("readiness_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("readiness_summary"), dict)
                else {}
            ),
            "readiness_blocked": (
                run_state_payload.get("readiness_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "readiness_manual_required": (
                run_state_payload.get("readiness_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "readiness_awaiting_prerequisites": (
                run_state_payload.get("readiness_awaiting_prerequisites")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "commit_execution_summary": (
                dict(run_state_payload.get("commit_execution_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("commit_execution_summary"), dict)
                else {}
            ),
            "commit_execution_executed": (
                run_state_payload.get("commit_execution_executed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "commit_execution_pending": (
                run_state_payload.get("commit_execution_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "commit_execution_failed": (
                run_state_payload.get("commit_execution_failed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "commit_execution_manual_intervention_required": (
                run_state_payload.get("commit_execution_manual_intervention_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "push_execution_summary": (
                dict(run_state_payload.get("push_execution_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("push_execution_summary"), dict)
                else {}
            ),
            "pr_execution_summary": (
                dict(run_state_payload.get("pr_execution_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("pr_execution_summary"), dict)
                else {}
            ),
            "merge_execution_summary": (
                dict(run_state_payload.get("merge_execution_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("merge_execution_summary"), dict)
                else {}
            ),
            "push_execution_succeeded": (
                run_state_payload.get("push_execution_succeeded")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "pr_execution_succeeded": (
                run_state_payload.get("pr_execution_succeeded")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "merge_execution_succeeded": (
                run_state_payload.get("merge_execution_succeeded")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "push_execution_pending": (
                run_state_payload.get("push_execution_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "pr_execution_pending": (
                run_state_payload.get("pr_execution_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "merge_execution_pending": (
                run_state_payload.get("merge_execution_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "push_execution_failed": (
                run_state_payload.get("push_execution_failed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "pr_execution_failed": (
                run_state_payload.get("pr_execution_failed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "merge_execution_failed": (
                run_state_payload.get("merge_execution_failed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "delivery_execution_manual_intervention_required": (
                run_state_payload.get("delivery_execution_manual_intervention_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_execution_summary": (
                dict(run_state_payload.get("rollback_execution_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("rollback_execution_summary"), dict)
                else {}
            ),
            "rollback_execution_attempted": (
                run_state_payload.get("rollback_execution_attempted")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_execution_succeeded": (
                run_state_payload.get("rollback_execution_succeeded")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_execution_pending": (
                run_state_payload.get("rollback_execution_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_execution_failed": (
                run_state_payload.get("rollback_execution_failed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_execution_manual_intervention_required": (
                run_state_payload.get("rollback_execution_manual_intervention_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_replan_required": (
                run_state_payload.get("rollback_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_automatic_continuation_blocked": (
                run_state_payload.get("rollback_automatic_continuation_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_aftermath_summary": (
                dict(run_state_payload.get("rollback_aftermath_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("rollback_aftermath_summary"), dict)
                else {}
            ),
            "rollback_aftermath_status": (
                run_state_payload.get("rollback_aftermath_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_aftermath_blocked": (
                run_state_payload.get("rollback_aftermath_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_aftermath_manual_required": (
                run_state_payload.get("rollback_aftermath_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_aftermath_missing_or_ambiguous": (
                run_state_payload.get("rollback_aftermath_missing_or_ambiguous")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_aftermath_blocked_reason": (
                run_state_payload.get("rollback_aftermath_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_aftermath_blocked_reasons": (
                [str(item) for item in run_state_payload.get("rollback_aftermath_blocked_reasons", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("rollback_aftermath_blocked_reasons"), (list, tuple))
                else []
            ),
            "rollback_remote_followup_required": (
                run_state_payload.get("rollback_remote_followup_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_manual_followup_required": (
                run_state_payload.get("rollback_manual_followup_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_validation_failed": (
                run_state_payload.get("rollback_validation_failed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "authority_validation_summary": (
                dict(run_state_payload.get("authority_validation_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("authority_validation_summary"), dict)
                else {}
            ),
            "authority_validation_blocked": (
                run_state_payload.get("authority_validation_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authority_blocked": (
                run_state_payload.get("execution_authority_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "validation_blocked": (
                run_state_payload.get("validation_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "authority_validation_manual_required": (
                run_state_payload.get("authority_validation_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "authority_validation_missing_or_ambiguous": (
                run_state_payload.get("authority_validation_missing_or_ambiguous")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "authority_validation_blocked_reason": (
                run_state_payload.get("authority_validation_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "authority_validation_blocked_reasons": (
                [str(item) for item in run_state_payload.get("authority_validation_blocked_reasons", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("authority_validation_blocked_reasons"), (list, tuple))
                else []
            ),
            "remote_github_summary": (
                dict(run_state_payload.get("remote_github_summary"))
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("remote_github_summary"), dict)
                else {}
            ),
            "remote_github_blocked": (
                run_state_payload.get("remote_github_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "remote_github_manual_required": (
                run_state_payload.get("remote_github_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "remote_github_missing_or_ambiguous": (
                run_state_payload.get("remote_github_missing_or_ambiguous")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "remote_github_blocked_reason": (
                run_state_payload.get("remote_github_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "remote_github_blocked_reasons": (
                [str(item) for item in run_state_payload.get("remote_github_blocked_reasons", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("remote_github_blocked_reasons"), (list, tuple))
                else []
            ),
            "policy_status": (
                run_state_payload.get("policy_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_blocked": (
                run_state_payload.get("policy_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_manual_required": (
                run_state_payload.get("policy_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_replan_required": (
                run_state_payload.get("policy_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_resume_allowed": (
                run_state_payload.get("policy_resume_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_terminal": (
                run_state_payload.get("policy_terminal")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_blocked_reason": (
                run_state_payload.get("policy_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_blocked_reasons": (
                [str(item) for item in run_state_payload.get("policy_blocked_reasons", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("policy_blocked_reasons"), (list, tuple))
                else []
            ),
            "policy_primary_blocker_class": (
                run_state_payload.get("policy_primary_blocker_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_primary_action": (
                run_state_payload.get("policy_primary_action")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "policy_allowed_actions": (
                [str(item) for item in run_state_payload.get("policy_allowed_actions", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("policy_allowed_actions"), (list, tuple))
                else []
            ),
            "policy_disallowed_actions": (
                [str(item) for item in run_state_payload.get("policy_disallowed_actions", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("policy_disallowed_actions"), (list, tuple))
                else []
            ),
            "policy_manual_actions": (
                [str(item) for item in run_state_payload.get("policy_manual_actions", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("policy_manual_actions"), (list, tuple))
                else []
            ),
            "policy_resumable_reason": (
                run_state_payload.get("policy_resumable_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_closure_status": (
                run_state_payload.get("lifecycle_closure_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_safely_closed": (
                run_state_payload.get("lifecycle_safely_closed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_terminal": (
                run_state_payload.get("lifecycle_terminal")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_resumable": (
                run_state_payload.get("lifecycle_resumable")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_manual_required": (
                run_state_payload.get("lifecycle_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_replan_required": (
                run_state_payload.get("lifecycle_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_execution_complete_not_closed": (
                run_state_payload.get("lifecycle_execution_complete_not_closed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_rollback_complete_not_closed": (
                run_state_payload.get("lifecycle_rollback_complete_not_closed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_blocked_reason": (
                run_state_payload.get("lifecycle_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_blocked_reasons": (
                [str(item) for item in run_state_payload.get("lifecycle_blocked_reasons", [])]
                if isinstance(run_state_payload, dict)
                and isinstance(run_state_payload.get("lifecycle_blocked_reasons"), (list, tuple))
                else []
            ),
            "lifecycle_primary_closure_issue": (
                run_state_payload.get("lifecycle_primary_closure_issue")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lifecycle_stop_class": (
                run_state_payload.get("lifecycle_stop_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
        }),
    }


def _derive_validation_status(result_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result_payload, dict):
        return {"verify_status": None, "verify_reason": None}

    execution = result_payload.get("execution")
    if not isinstance(execution, dict):
        return {"verify_status": None, "verify_reason": None}

    verify = execution.get("verify")
    if isinstance(verify, dict):
        return {
            "verify_status": verify.get("status"),
            "verify_reason": verify.get("reason"),
        }

    return {"verify_status": None, "verify_reason": None}


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _default_write_authority_surface() -> dict[str, Any]:
    return {
        "state": None,
        "allowed_categories": [],
    }


def _default_merge_gate_contract_surface() -> dict[str, Any]:
    return {
        "lifecycle_state": None,
        "write_authority": _default_write_authority_surface(),
        "failure_type": None,
        "retry_recommended": None,
        "retry_recommendation": None,
        "retry_budget_remaining": None,
        "escalation_required": None,
        "next_action_readiness": None,
        "primary_fail_reasons": [],
    }


def _derive_merge_gate_contract_surface(
    merge_gate_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    surface = _default_merge_gate_contract_surface()
    if not isinstance(merge_gate_payload, dict):
        return surface

    raw_lifecycle_state = merge_gate_payload.get("lifecycle_state")
    if raw_lifecycle_state is not None:
        text = str(raw_lifecycle_state).strip()
        surface["lifecycle_state"] = text if text else None

    raw_write_authority = merge_gate_payload.get("write_authority")
    if isinstance(raw_write_authority, dict):
        raw_state = raw_write_authority.get("state")
        if raw_state is not None:
            text = str(raw_state).strip()
            surface["write_authority"]["state"] = text if text else None
        surface["write_authority"]["allowed_categories"] = _normalize_string_list(
            raw_write_authority.get("allowed_categories")
        )

    replan_input = merge_gate_payload.get("replan_input")
    if isinstance(replan_input, dict):
        raw_failure_type = replan_input.get("failure_type")
        if raw_failure_type is not None:
            text = str(raw_failure_type).strip()
            surface["failure_type"] = text if text else None
        surface["retry_recommended"] = _as_optional_bool(replan_input.get("retry_recommended"))

        raw_retry_recommendation = replan_input.get("retry_recommendation")
        if raw_retry_recommendation is not None:
            text = str(raw_retry_recommendation).strip()
            surface["retry_recommendation"] = text if text else None

        raw_retry_budget_remaining = replan_input.get("retry_budget_remaining")
        if isinstance(raw_retry_budget_remaining, bool):
            surface["retry_budget_remaining"] = None
        elif isinstance(raw_retry_budget_remaining, int):
            surface["retry_budget_remaining"] = raw_retry_budget_remaining
        elif isinstance(raw_retry_budget_remaining, str) and raw_retry_budget_remaining.strip().isdigit():
            surface["retry_budget_remaining"] = int(raw_retry_budget_remaining.strip())
        else:
            surface["retry_budget_remaining"] = None

        surface["escalation_required"] = _as_optional_bool(replan_input.get("escalation_required"))

        raw_next_action_readiness = replan_input.get("next_action_readiness")
        if raw_next_action_readiness is not None:
            text = str(raw_next_action_readiness).strip()
            surface["next_action_readiness"] = text if text else None

        surface["primary_fail_reasons"] = _normalize_string_list(
            replan_input.get("primary_fail_reasons")
        )

    return surface


def _derive_output_dir(row: dict[str, Any], *, out_dir_arg: str | None) -> Path:
    if out_dir_arg:
        return Path(out_dir_arg)

    result_path = row.get("result_path")
    if isinstance(result_path, str) and result_path.strip():
        return Path(result_path).resolve().parent

    return Path.cwd()


def _build_summary(row: dict[str, Any], *, db_path: str) -> dict[str, Any]:
    result_payload = _read_json(row.get("result_path"))
    merge_gate_payload = _read_json(row.get("merge_gate_path"))
    merge_gate_surface = _derive_merge_gate_contract_surface(merge_gate_payload)
    lifecycle_artifacts = _read_lifecycle_artifacts(row.get("result_path"))
    rollback_trace = get_rollback_trace_by_job_id(str(row.get("job_id", "")), db_path=db_path)
    rollback_execution = get_rollback_execution_by_job_id(str(row.get("job_id", "")), db_path=db_path)

    validation = _derive_validation_status(result_payload)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": row.get("repo"),
        "job_id": row.get("job_id"),
        "accepted_status": row.get("accepted_status"),
        "declared_category": row.get("declared_category"),
        "observed_category": row.get("observed_category"),
        "validation": validation,
        "lifecycle_state": merge_gate_surface["lifecycle_state"],
        "write_authority": merge_gate_surface["write_authority"],
        "failure_type": merge_gate_surface["failure_type"],
        "retry_recommended": merge_gate_surface["retry_recommended"],
        "retry_recommendation": merge_gate_surface["retry_recommendation"],
        "retry_budget_remaining": merge_gate_surface["retry_budget_remaining"],
        "escalation_required": merge_gate_surface["escalation_required"],
        "next_action_readiness": merge_gate_surface["next_action_readiness"],
        "primary_fail_reasons": merge_gate_surface["primary_fail_reasons"],
        "merge": {
            "merge_eligible": _as_optional_bool(row.get("merge_eligible")),
            "merge_gate_passed": _as_optional_bool(row.get("merge_gate_passed")),
        },
        "rollback": {
            "trace_recorded": rollback_trace is not None,
            "rollback_trace_id": rollback_trace.get("rollback_trace_id") if rollback_trace else None,
            "rollback_eligible": (
                _as_optional_bool(rollback_trace.get("rollback_eligible"))
                if rollback_trace
                else None
            ),
            "rollback_execution_recorded": rollback_execution is not None,
            "rollback_execution_status": (
                rollback_execution.get("execution_status") if rollback_execution else None
            ),
        },
        "paths": {
            "request": row.get("request_path"),
            "result": row.get("result_path"),
            "rubric": row.get("rubric_path"),
            "merge_gate": row.get("merge_gate_path"),
            "classification": row.get("classification_path"),
        },
        "lifecycle_artifacts": lifecycle_artifacts,
    }


def _normalize_changed_files(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _derive_changed_files(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    classification_payload: dict[str, Any] | None,
) -> list[str]:
    if isinstance(classification_payload, dict):
        changed = _normalize_changed_files(classification_payload.get("changed_files"))
        if changed:
            return changed

    if isinstance(request_payload, dict):
        changed = _normalize_changed_files(request_payload.get("changed_files"))
        if changed:
            return changed

    if isinstance(result_payload, dict):
        changed = _normalize_changed_files(result_payload.get("changed_files"))
        if changed:
            return changed
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            changed = _normalize_changed_files(execution.get("changed_files"))
            if changed:
                return changed
    return []


def _derive_int_signal(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    key: str,
) -> int:
    candidates: list[Any] = []
    if isinstance(result_payload, dict):
        candidates.append(result_payload.get(key))
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            candidates.append(execution.get(key))
    if isinstance(request_payload, dict):
        candidates.append(request_payload.get(key))

    for value in candidates:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped.lstrip("-").isdigit():
                return int(stripped)
    return 0


def _derive_required_tests_signals(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    rubric_payload: dict[str, Any] | None,
) -> tuple[bool, bool, bool]:
    if isinstance(rubric_payload, dict):
        declared = _as_optional_bool(rubric_payload.get("required_tests_declared"))
        executed = _as_optional_bool(rubric_payload.get("required_tests_executed"))
        passed = _as_optional_bool(rubric_payload.get("required_tests_passed"))
        if declared is not None and executed is not None and passed is not None:
            return declared, executed, passed

    declared = False
    if isinstance(request_payload, dict):
        validation_commands = request_payload.get("validation_commands")
        if isinstance(validation_commands, list):
            declared = len(validation_commands) > 0

    verify_status = ""
    if isinstance(result_payload, dict):
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            verify = execution.get("verify")
            if isinstance(verify, dict):
                verify_status = str(verify.get("status", "")).strip().lower()

    if verify_status == "passed":
        return declared, True, True
    if verify_status == "failed":
        return declared, True, False
    return declared, False, False


def _derive_prompt_contract_compliance(
    request_payload: dict[str, Any] | None,
) -> bool | None:
    if not isinstance(request_payload, dict):
        return None
    explicit = _as_optional_bool(request_payload.get("prompt_contract_compliant"))
    if explicit is not None:
        return explicit
    required = ("repo", "task_type", "goal", "provider")
    for key in required:
        value = request_payload.get(key)
        if value is None or not str(value).strip():
            return None
    validation_commands = request_payload.get("validation_commands")
    if not isinstance(validation_commands, list):
        return None
    return True


def _build_policy_facts(summary: dict[str, Any]) -> dict[str, Any]:
    paths = summary.get("paths", {})
    request_payload = _read_json(paths.get("request")) if isinstance(paths, dict) else None
    result_payload = _read_json(paths.get("result")) if isinstance(paths, dict) else None
    rubric_payload = _read_json(paths.get("rubric")) if isinstance(paths, dict) else None
    merge_gate_payload = _read_json(paths.get("merge_gate")) if isinstance(paths, dict) else None
    classification_payload = _read_json(paths.get("classification")) if isinstance(paths, dict) else None

    execution_payload = (
        result_payload.get("execution")
        if isinstance(result_payload, dict) and isinstance(result_payload.get("execution"), dict)
        else {}
    )
    verify_payload = (
        execution_payload.get("verify")
        if isinstance(execution_payload.get("verify"), dict)
        else {}
    )

    rollback = summary.get("rollback", {})
    merge = summary.get("merge", {})
    required_declared, required_executed, required_passed = _derive_required_tests_signals(
        request_payload=request_payload,
        result_payload=result_payload,
        rubric_payload=rubric_payload,
    )

    return {
        "accepted_status": summary.get("accepted_status"),
        "execution_status": execution_payload.get("status"),
        "verify_status": verify_payload.get("status"),
        "verify_reason": verify_payload.get("reason"),
        "declared_category": summary.get("declared_category"),
        "observed_category": summary.get("observed_category"),
        "changed_files": _derive_changed_files(
            request_payload=request_payload,
            result_payload=result_payload,
            classification_payload=classification_payload,
        ),
        "additions": _derive_int_signal(
            request_payload=request_payload,
            result_payload=result_payload,
            key="additions",
        ),
        "deletions": _derive_int_signal(
            request_payload=request_payload,
            result_payload=result_payload,
            key="deletions",
        ),
        "required_tests_declared": required_declared,
        "required_tests_executed": required_executed,
        "required_tests_passed": required_passed,
        "merge_eligible": (
            _as_optional_bool(rubric_payload.get("merge_eligible"))
            if isinstance(rubric_payload, dict)
            else _as_optional_bool(merge.get("merge_eligible"))
        ),
        "merge_gate_passed": (
            _as_optional_bool(merge_gate_payload.get("passed"))
            if isinstance(merge_gate_payload, dict)
            else _as_optional_bool(merge.get("merge_gate_passed"))
        ),
        "forbidden_files_untouched": (
            _as_optional_bool(rubric_payload.get("forbidden_files_untouched"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "diff_size_within_limit": (
            _as_optional_bool(rubric_payload.get("diff_size_within_limit"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "runtime_semantics_changed": (
            _as_optional_bool(rubric_payload.get("runtime_semantics_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "contract_shape_changed": (
            _as_optional_bool(rubric_payload.get("contract_shape_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "reviewer_fields_changed": (
            _as_optional_bool(rubric_payload.get("reviewer_fields_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "rubric_fail_reasons": (
            rubric_payload.get("fail_reasons")
            if isinstance(rubric_payload, dict)
            else []
        ),
        "rubric_warnings": (
            rubric_payload.get("warnings")
            if isinstance(rubric_payload, dict)
            else []
        ),
        "merge_gate_fail_reasons": (
            merge_gate_payload.get("fail_reasons")
            if isinstance(merge_gate_payload, dict)
            else []
        ),
        "rollback_trace_recorded": (
            _as_optional_bool(rollback.get("trace_recorded")) if isinstance(rollback, dict) else None
        ),
        "rollback_eligible": (
            _as_optional_bool(rollback.get("rollback_eligible")) if isinstance(rollback, dict) else None
        ),
        "rollback_execution_status": (
            rollback.get("rollback_execution_status") if isinstance(rollback, dict) else None
        ),
        "prompt_contract_compliant": _derive_prompt_contract_compliance(request_payload),
    }


def _normalize_changed_files(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _derive_changed_files(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    classification_payload: dict[str, Any] | None,
) -> list[str]:
    if isinstance(classification_payload, dict):
        changed = _normalize_changed_files(classification_payload.get("changed_files"))
        if changed:
            return changed

    if isinstance(request_payload, dict):
        changed = _normalize_changed_files(request_payload.get("changed_files"))
        if changed:
            return changed

    if isinstance(result_payload, dict):
        changed = _normalize_changed_files(result_payload.get("changed_files"))
        if changed:
            return changed
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            changed = _normalize_changed_files(execution.get("changed_files"))
            if changed:
                return changed
    return []


def _derive_int_signal(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    key: str,
) -> int:
    candidates: list[Any] = []
    if isinstance(result_payload, dict):
        candidates.append(result_payload.get(key))
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            candidates.append(execution.get(key))
    if isinstance(request_payload, dict):
        candidates.append(request_payload.get(key))

    for value in candidates:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if stripped and stripped.lstrip("-").isdigit():
                return int(stripped)
    return 0


def _derive_required_tests_signals(
    *,
    request_payload: dict[str, Any] | None,
    result_payload: dict[str, Any] | None,
    rubric_payload: dict[str, Any] | None,
) -> tuple[bool, bool, bool]:
    if isinstance(rubric_payload, dict):
        declared = _as_optional_bool(rubric_payload.get("required_tests_declared"))
        executed = _as_optional_bool(rubric_payload.get("required_tests_executed"))
        passed = _as_optional_bool(rubric_payload.get("required_tests_passed"))
        if declared is not None and executed is not None and passed is not None:
            return declared, executed, passed

    declared = False
    if isinstance(request_payload, dict):
        validation_commands = request_payload.get("validation_commands")
        if isinstance(validation_commands, list):
            declared = len(validation_commands) > 0

    verify_status = ""
    if isinstance(result_payload, dict):
        execution = result_payload.get("execution")
        if isinstance(execution, dict):
            verify = execution.get("verify")
            if isinstance(verify, dict):
                verify_status = str(verify.get("status", "")).strip().lower()

    if verify_status == "passed":
        return declared, True, True
    if verify_status == "failed":
        return declared, True, False
    return declared, False, False


def _derive_prompt_contract_compliance(
    request_payload: dict[str, Any] | None,
) -> bool | None:
    if not isinstance(request_payload, dict):
        return None
    explicit = _as_optional_bool(request_payload.get("prompt_contract_compliant"))
    if explicit is not None:
        return explicit
    required = ("repo", "task_type", "goal", "provider")
    for key in required:
        value = request_payload.get(key)
        if value is None or not str(value).strip():
            return None
    validation_commands = request_payload.get("validation_commands")
    if not isinstance(validation_commands, list):
        return None
    return True


def _build_policy_facts(summary: dict[str, Any]) -> dict[str, Any]:
    paths = summary.get("paths", {})
    request_payload = _read_json(paths.get("request")) if isinstance(paths, dict) else None
    result_payload = _read_json(paths.get("result")) if isinstance(paths, dict) else None
    rubric_payload = _read_json(paths.get("rubric")) if isinstance(paths, dict) else None
    merge_gate_payload = _read_json(paths.get("merge_gate")) if isinstance(paths, dict) else None
    classification_payload = _read_json(paths.get("classification")) if isinstance(paths, dict) else None

    execution_payload = (
        result_payload.get("execution")
        if isinstance(result_payload, dict) and isinstance(result_payload.get("execution"), dict)
        else {}
    )
    verify_payload = (
        execution_payload.get("verify")
        if isinstance(execution_payload.get("verify"), dict)
        else {}
    )

    rollback = summary.get("rollback", {})
    merge = summary.get("merge", {})
    required_declared, required_executed, required_passed = _derive_required_tests_signals(
        request_payload=request_payload,
        result_payload=result_payload,
        rubric_payload=rubric_payload,
    )

    return {
        "accepted_status": summary.get("accepted_status"),
        "execution_status": execution_payload.get("status"),
        "verify_status": verify_payload.get("status"),
        "verify_reason": verify_payload.get("reason"),
        "declared_category": summary.get("declared_category"),
        "observed_category": summary.get("observed_category"),
        "changed_files": _derive_changed_files(
            request_payload=request_payload,
            result_payload=result_payload,
            classification_payload=classification_payload,
        ),
        "additions": _derive_int_signal(
            request_payload=request_payload,
            result_payload=result_payload,
            key="additions",
        ),
        "deletions": _derive_int_signal(
            request_payload=request_payload,
            result_payload=result_payload,
            key="deletions",
        ),
        "required_tests_declared": required_declared,
        "required_tests_executed": required_executed,
        "required_tests_passed": required_passed,
        "merge_eligible": (
            _as_optional_bool(rubric_payload.get("merge_eligible"))
            if isinstance(rubric_payload, dict)
            else _as_optional_bool(merge.get("merge_eligible"))
        ),
        "merge_gate_passed": (
            _as_optional_bool(merge_gate_payload.get("passed"))
            if isinstance(merge_gate_payload, dict)
            else _as_optional_bool(merge.get("merge_gate_passed"))
        ),
        "forbidden_files_untouched": (
            _as_optional_bool(rubric_payload.get("forbidden_files_untouched"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "diff_size_within_limit": (
            _as_optional_bool(rubric_payload.get("diff_size_within_limit"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "runtime_semantics_changed": (
            _as_optional_bool(rubric_payload.get("runtime_semantics_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "contract_shape_changed": (
            _as_optional_bool(rubric_payload.get("contract_shape_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "reviewer_fields_changed": (
            _as_optional_bool(rubric_payload.get("reviewer_fields_changed"))
            if isinstance(rubric_payload, dict)
            else None
        ),
        "rubric_fail_reasons": (
            rubric_payload.get("fail_reasons")
            if isinstance(rubric_payload, dict)
            else []
        ),
        "rubric_warnings": (
            rubric_payload.get("warnings")
            if isinstance(rubric_payload, dict)
            else []
        ),
        "merge_gate_fail_reasons": (
            merge_gate_payload.get("fail_reasons")
            if isinstance(merge_gate_payload, dict)
            else []
        ),
        "rollback_trace_recorded": (
            _as_optional_bool(rollback.get("trace_recorded")) if isinstance(rollback, dict) else None
        ),
        "rollback_eligible": (
            _as_optional_bool(rollback.get("rollback_eligible")) if isinstance(rollback, dict) else None
        ),
        "rollback_execution_status": (
            rollback.get("rollback_execution_status") if isinstance(rollback, dict) else None
        ),
        "prompt_contract_compliant": _derive_prompt_contract_compliance(request_payload),
    }


def _build_machine_review_payload(
    summary: dict[str, Any],
    *,
    summary_json_path: Path,
    summary_html_path: Path,
    machine_payload_path: Path,
) -> dict[str, Any]:
    merge = summary.get("merge")
    rollback = summary.get("rollback")
    validation = summary.get("validation")
    paths = summary.get("paths")

    merge_eligible = None
    merge_gate_passed = None
    if isinstance(merge, dict):
        merge_eligible = merge.get("merge_eligible")
        merge_gate_passed = merge.get("merge_gate_passed")

    rollback_eligible = None
    rollback_trace_recorded = None
    rollback_execution_status = None
    rollback_trace_id = None
    if isinstance(rollback, dict):
        rollback_eligible = rollback.get("rollback_eligible")
        rollback_trace_recorded = rollback.get("trace_recorded")
        rollback_execution_status = rollback.get("rollback_execution_status")
        rollback_trace_id = rollback.get("rollback_trace_id")

    verify_status = None
    verify_reason = None
    if isinstance(validation, dict):
        verify_status = validation.get("verify_status")
        verify_reason = validation.get("verify_reason")

    artifact_references: dict[str, Any] = {
        "operator_summary_json": str(summary_json_path),
        "operator_summary_html": str(summary_html_path),
        "machine_review_payload": str(machine_payload_path),
    }
    if isinstance(paths, dict):
        for key in ("request", "result", "rubric", "merge_gate", "classification"):
            artifact_references[key] = paths.get(key)
    lifecycle = summary.get("lifecycle_artifacts")
    if isinstance(lifecycle, dict):
        lifecycle_paths = lifecycle.get("paths")
        if isinstance(lifecycle_paths, dict):
            for key in (
                "checkpoint_decision",
                "commit_decision",
                "merge_decision",
                "rollback_decision",
                "commit_execution",
                "push_execution",
                "pr_execution",
                "merge_execution",
                "rollback_execution",
                "run_state",
            ):
                artifact_references[key] = lifecycle_paths.get(key)

    policy_output = evaluate_recovery_policy(_build_policy_facts(summary))
    recovery_decision = str(policy_output.get("recovery_decision", "")).strip().lower()
    decision_basis = (
        [str(item) for item in policy_output.get("decision_basis", [])]
        if isinstance(policy_output.get("decision_basis"), (list, tuple))
        else []
    )
    failure_codes = (
        [str(item) for item in policy_output.get("failure_codes", [])]
        if isinstance(policy_output.get("failure_codes"), (list, tuple))
        else []
    )

    policy_output = evaluate_recovery_policy(_build_policy_facts(summary))
    recovery_decision = str(policy_output.get("recovery_decision", "")).strip().lower()
    decision_basis = (
        [str(item) for item in policy_output.get("decision_basis", [])]
        if isinstance(policy_output.get("decision_basis"), (list, tuple))
        else []
    )
    failure_codes = (
        [str(item) for item in policy_output.get("failure_codes", [])]
        if isinstance(policy_output.get("failure_codes"), (list, tuple))
        else []
    )

    payload = {
        "schema_version": "1.1",
        "action_vocabulary": (
            "keep",
            "revise_current_state",
            "reset_and_retry",
            "escalate",
        ),
        "job_id": summary.get("job_id"),
        "repo": summary.get("repo"),
        "accepted_status": summary.get("accepted_status"),
        "merge_eligible": merge_eligible,
        "merge_gate_passed": merge_gate_passed,
        "rollback_eligible": rollback_eligible,
        "rollback_trace_id": rollback_trace_id,
        "validation": {
            "verify_status": verify_status,
            "verify_reason": verify_reason,
        },
        "guardrail_flags": {
            "rollback_trace_recorded": rollback_trace_recorded,
            "rollback_execution_status": rollback_execution_status,
        },
        "artifact_references": artifact_references,
        "policy_version": policy_output.get("policy_version", POLICY_VERSION),
        "score_total": policy_output.get("score_total"),
        "dimension_scores": policy_output.get("dimension_scores", {}),
        "failure_codes": failure_codes,
        "recovery_decision": recovery_decision,
        "decision_basis": decision_basis,
        "requires_human_review": bool(policy_output.get("requires_human_review", True)),
        "recommended_action": recovery_decision,
        "policy_reasons": failure_codes,
        "lifecycle_state": summary.get("lifecycle_state"),
        "write_authority": summary.get("write_authority"),
        "failure_type": summary.get("failure_type"),
        "retry_recommended": summary.get("retry_recommended"),
        "retry_recommendation": summary.get("retry_recommendation"),
        "retry_budget_remaining": summary.get("retry_budget_remaining"),
        "escalation_required": summary.get("escalation_required"),
        "next_action_readiness": summary.get("next_action_readiness"),
        "primary_fail_reasons": summary.get("primary_fail_reasons"),
    }
    payload["retry_metadata"] = _build_retry_metadata(
        recovery_decision=recovery_decision,
        decision_basis=decision_basis,
    )
    return payload


def _build_retry_metadata(
    *,
    recovery_decision: Any,
    decision_basis: Any,
) -> dict[str, Any]:
    normalized_decision = str(recovery_decision or "").strip().lower()
    normalized_basis = (
        [str(reason) for reason in decision_basis]
        if isinstance(decision_basis, (list, tuple))
        else []
    )

    if normalized_decision == "reset_and_retry":
        return {
            "retry_recommended": True,
            "retry_basis": normalized_basis,
            "retry_blockers": [],
        }

    if normalized_decision in {"keep", "revise_current_state"}:
        return {
            "retry_recommended": False,
            "retry_basis": [],
            "retry_blockers": normalized_basis,
        }

    # Escalation is explicit-human-review territory.
    return {
        "retry_recommended": None,
        "retry_basis": [],
        "retry_blockers": normalized_basis,
    }


def _to_html(summary: dict[str, Any]) -> str:
    def line(label: str, value: Any) -> str:
        text = "<missing>" if value is None else str(value)
        return (
            '<div class="row">'
            f'<div class="label">{escape(label)}</div>'
            f'<div class="value">{escape(text)}</div>'
            "</div>"
        )

    rows = []
    rows.append(line("repo", summary.get("repo")))
    rows.append(line("job_id", summary.get("job_id")))
    rows.append(line("accepted_status", summary.get("accepted_status")))

    validation = summary.get("validation", {})
    if isinstance(validation, dict):
        rows.append(line("verify_status", validation.get("verify_status")))
        rows.append(line("verify_reason", validation.get("verify_reason")))
    rows.append(line("lifecycle_state", summary.get("lifecycle_state")))
    write_authority = summary.get("write_authority")
    if isinstance(write_authority, dict):
        rows.append(line("write_authority.state", write_authority.get("state")))
        rows.append(
            line(
                "write_authority.allowed_categories",
                ", ".join(_normalize_string_list(write_authority.get("allowed_categories"))) or None,
            )
        )
    rows.append(line("failure_type", summary.get("failure_type")))
    rows.append(line("retry_recommended", summary.get("retry_recommended")))
    rows.append(line("retry_recommendation", summary.get("retry_recommendation")))
    rows.append(line("retry_budget_remaining", summary.get("retry_budget_remaining")))
    rows.append(line("escalation_required", summary.get("escalation_required")))
    rows.append(line("next_action_readiness", summary.get("next_action_readiness")))
    rows.append(
        line(
            "primary_fail_reasons",
            ", ".join(_normalize_string_list(summary.get("primary_fail_reasons"))) or None,
        )
    )

    merge = summary.get("merge", {})
    if isinstance(merge, dict):
        rows.append(line("merge_eligible", merge.get("merge_eligible")))
        rows.append(line("merge_gate_passed", merge.get("merge_gate_passed")))

    rollback = summary.get("rollback", {})
    if isinstance(rollback, dict):
        rows.append(line("rollback_trace_recorded", rollback.get("trace_recorded")))
        rows.append(line("rollback_eligible", rollback.get("rollback_eligible")))
        rows.append(line("rollback_execution_status", rollback.get("rollback_execution_status")))

    lifecycle = summary.get("lifecycle_artifacts", {})
    if isinstance(lifecycle, dict):
        checkpoint_decision = lifecycle.get("checkpoint_decision")
        commit_decision = lifecycle.get("commit_decision")
        merge_decision = lifecycle.get("merge_decision")
        rollback_decision = lifecycle.get("rollback_decision")
        commit_execution = lifecycle.get("commit_execution")
        push_execution = lifecycle.get("push_execution")
        pr_execution = lifecycle.get("pr_execution")
        merge_execution = lifecycle.get("merge_execution")
        rollback_execution = lifecycle.get("rollback_execution")
        run_state = lifecycle.get("run_state")
        paths = lifecycle.get("paths")
        if isinstance(checkpoint_decision, dict):
            rows.append(line("lifecycle.checkpoint_stage", checkpoint_decision.get("checkpoint_stage")))
            rows.append(line("lifecycle.checkpoint_decision", checkpoint_decision.get("decision")))
            rows.append(
                line(
                    "lifecycle.checkpoint_manual_intervention_required",
                    checkpoint_decision.get("manual_intervention_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.checkpoint_global_stop_recommended",
                    checkpoint_decision.get("global_stop_recommended"),
                )
            )
        if isinstance(commit_decision, dict):
            rows.append(line("lifecycle.commit_decision", commit_decision.get("decision")))
        if isinstance(merge_decision, dict):
            rows.append(line("lifecycle.merge_decision", merge_decision.get("decision")))
        if isinstance(rollback_decision, dict):
            rows.append(line("lifecycle.rollback_decision", rollback_decision.get("decision")))
        if isinstance(commit_execution, dict):
            rows.append(line("lifecycle.commit_execution_status", commit_execution.get("status")))
            rows.append(line("lifecycle.commit_execution_commit_sha", commit_execution.get("commit_sha")))
            rows.append(
                line(
                    "lifecycle.commit_execution_authority_status",
                    commit_execution.get("execution_authority_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.commit_execution_validation_status",
                    commit_execution.get("validation_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.commit_execution_manual_intervention_required",
                    commit_execution.get("manual_intervention_required"),
                )
            )
        if isinstance(push_execution, dict):
            rows.append(line("lifecycle.push_execution_status", push_execution.get("status")))
            rows.append(line("lifecycle.push_execution_branch_name", push_execution.get("branch_name")))
            rows.append(line("lifecycle.push_remote_state_status", push_execution.get("remote_state_status")))
            rows.append(
                line(
                    "lifecycle.push_remote_state_blocked_reason",
                    push_execution.get("remote_state_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.push_execution_authority_status",
                    push_execution.get("execution_authority_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.push_execution_validation_status",
                    push_execution.get("validation_status"),
                )
            )
        if isinstance(pr_execution, dict):
            rows.append(line("lifecycle.pr_execution_status", pr_execution.get("status")))
            rows.append(line("lifecycle.pr_execution_pr_number", pr_execution.get("pr_number")))
            rows.append(line("lifecycle.pr_existing_pr_status", pr_execution.get("existing_pr_status")))
            rows.append(
                line(
                    "lifecycle.pr_creation_state_status",
                    pr_execution.get("pr_creation_state_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.pr_remote_state_blocked_reason",
                    pr_execution.get("remote_state_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.pr_execution_authority_status",
                    pr_execution.get("execution_authority_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.pr_execution_validation_status",
                    pr_execution.get("validation_status"),
                )
            )
        if isinstance(merge_execution, dict):
            rows.append(line("lifecycle.merge_execution_status", merge_execution.get("status")))
            rows.append(line("lifecycle.merge_execution_merge_commit_sha", merge_execution.get("merge_commit_sha")))
            rows.append(line("lifecycle.merge_mergeability_status", merge_execution.get("mergeability_status")))
            rows.append(
                line(
                    "lifecycle.merge_merge_requirements_status",
                    merge_execution.get("merge_requirements_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.merge_required_checks_status",
                    merge_execution.get("required_checks_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.merge_remote_state_blocked_reason",
                    merge_execution.get("remote_state_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.merge_execution_authority_status",
                    merge_execution.get("execution_authority_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.merge_execution_validation_status",
                    merge_execution.get("validation_status"),
                )
            )
        if isinstance(rollback_execution, dict):
            rows.append(line("lifecycle.rollback_execution_status", rollback_execution.get("status")))
            rows.append(line("lifecycle.rollback_execution_mode", rollback_execution.get("rollback_mode")))
            rows.append(
                line(
                    "lifecycle.rollback_execution_authority_status",
                    rollback_execution.get("execution_authority_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_execution_validation_status",
                    rollback_execution.get("validation_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_execution_resulting_commit_sha",
                    rollback_execution.get("resulting_commit_sha"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_execution_manual_intervention_required",
                    rollback_execution.get("manual_intervention_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_execution_replan_required",
                    rollback_execution.get("replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_aftermath_status",
                    rollback_execution.get("rollback_aftermath_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_aftermath_blocked",
                    rollback_execution.get("rollback_aftermath_blocked"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_aftermath_blocked_reason",
                    rollback_execution.get("rollback_aftermath_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_validation_status",
                    rollback_execution.get("rollback_validation_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_manual_followup_required",
                    rollback_execution.get("rollback_manual_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_remote_followup_required",
                    rollback_execution.get("rollback_remote_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_post_validation_status",
                    rollback_execution.get("rollback_post_validation_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_remote_state_status",
                    rollback_execution.get("rollback_remote_state_status"),
                )
            )
        if isinstance(run_state, dict):
            rows.append(line("lifecycle.run_state", run_state.get("state")))
            rows.append(line("lifecycle.orchestration_state", run_state.get("orchestration_state")))
            rows.append(line("lifecycle.global_stop", run_state.get("global_stop")))
            rows.append(line("lifecycle.continue_allowed", run_state.get("continue_allowed")))
            rows.append(line("lifecycle.run_paused", run_state.get("run_paused")))
            rows.append(
                line(
                    "lifecycle.manual_intervention_required",
                    run_state.get("manual_intervention_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_evaluation_pending",
                    run_state.get("rollback_evaluation_pending"),
                )
            )
            rows.append(
                line(
                    "lifecycle.global_stop_recommended",
                    run_state.get("global_stop_recommended"),
                )
            )
            rows.append(line("lifecycle.next_run_action", run_state.get("next_run_action")))
            rows.append(line("lifecycle.loop_state", run_state.get("loop_state")))
            rows.append(line("lifecycle.next_safe_action", run_state.get("next_safe_action")))
            rows.append(line("lifecycle.loop_blocked_reason", run_state.get("loop_blocked_reason")))
            rows.append(
                line(
                    "lifecycle.loop_blocked_reasons",
                    ", ".join([str(v) for v in run_state.get("loop_blocked_reasons", [])]),
                )
            )
            rows.append(line("lifecycle.resumable", run_state.get("resumable")))
            rows.append(line("lifecycle.terminal", run_state.get("terminal")))
            rows.append(
                line(
                    "lifecycle.loop_manual_intervention_required",
                    run_state.get("loop_manual_intervention_required"),
                )
            )
            rows.append(line("lifecycle.loop_replan_required", run_state.get("loop_replan_required")))
            rows.append(line("lifecycle.rollback_completed", run_state.get("rollback_completed")))
            rows.append(line("lifecycle.delivery_completed", run_state.get("delivery_completed")))
            rows.append(
                line(
                    "lifecycle.authority_validation_blocked",
                    run_state.get("authority_validation_blocked"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authority_blocked",
                    run_state.get("execution_authority_blocked"),
                )
            )
            rows.append(
                line(
                    "lifecycle.validation_blocked",
                    run_state.get("validation_blocked"),
                )
            )
            rows.append(
                line(
                    "lifecycle.authority_validation_manual_required",
                    run_state.get("authority_validation_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.authority_validation_missing_or_ambiguous",
                    run_state.get("authority_validation_missing_or_ambiguous"),
                )
            )
            rows.append(
                line(
                    "lifecycle.authority_validation_blocked_reason",
                    run_state.get("authority_validation_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.remote_github_blocked",
                    run_state.get("remote_github_blocked"),
                )
            )
            rows.append(
                line(
                    "lifecycle.remote_github_manual_required",
                    run_state.get("remote_github_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.remote_github_missing_or_ambiguous",
                    run_state.get("remote_github_missing_or_ambiguous"),
                )
            )
            rows.append(
                line(
                    "lifecycle.remote_github_blocked_reason",
                    run_state.get("remote_github_blocked_reason"),
                )
            )
            rows.append(line("lifecycle.policy_status", run_state.get("policy_status")))
            rows.append(line("lifecycle.policy_blocked", run_state.get("policy_blocked")))
            rows.append(
                line(
                    "lifecycle.policy_manual_required",
                    run_state.get("policy_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_replan_required",
                    run_state.get("policy_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_resume_allowed",
                    run_state.get("policy_resume_allowed"),
                )
            )
            rows.append(line("lifecycle.policy_terminal", run_state.get("policy_terminal")))
            rows.append(
                line(
                    "lifecycle.policy_blocked_reason",
                    run_state.get("policy_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_blocked_reasons",
                    ", ".join([str(v) for v in (run_state.get("policy_blocked_reasons") or [])]),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_primary_blocker_class",
                    run_state.get("policy_primary_blocker_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_primary_action",
                    run_state.get("policy_primary_action"),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_allowed_actions",
                    ", ".join([str(v) for v in (run_state.get("policy_allowed_actions") or [])]),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_disallowed_actions",
                    ", ".join([str(v) for v in (run_state.get("policy_disallowed_actions") or [])]),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_manual_actions",
                    ", ".join([str(v) for v in (run_state.get("policy_manual_actions") or [])]),
                )
            )
            rows.append(
                line(
                    "lifecycle.policy_resumable_reason",
                    run_state.get("policy_resumable_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_posture_summary",
                    run_state.get("operator_posture_summary"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_primary_blocker_class",
                    run_state.get("operator_primary_blocker_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_primary_action",
                    run_state.get("operator_primary_action"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_action_scope",
                    run_state.get("operator_action_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_resume_status",
                    run_state.get("operator_resume_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_next_safe_posture",
                    run_state.get("operator_next_safe_posture"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_guidance_summary",
                    run_state.get("operator_guidance_summary"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_safe_actions_summary",
                    run_state.get("operator_safe_actions_summary"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_unsafe_actions_summary",
                    run_state.get("operator_unsafe_actions_summary"),
                )
            )
            rows.append(
                line(
                    "lifecycle.closure_status",
                    run_state.get("lifecycle_closure_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.safely_closed",
                    run_state.get("lifecycle_safely_closed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.terminal_normalized",
                    run_state.get("lifecycle_terminal"),
                )
            )
            rows.append(
                line(
                    "lifecycle.resumable_normalized",
                    run_state.get("lifecycle_resumable"),
                )
            )
            rows.append(
                line(
                    "lifecycle.manual_required_normalized",
                    run_state.get("lifecycle_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.replan_required_normalized",
                    run_state.get("lifecycle_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_complete_not_closed",
                    run_state.get("lifecycle_execution_complete_not_closed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_complete_not_closed",
                    run_state.get("lifecycle_rollback_complete_not_closed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.primary_closure_issue",
                    run_state.get("lifecycle_primary_closure_issue"),
                )
            )
            rows.append(
                line(
                    "lifecycle.stop_class",
                    run_state.get("lifecycle_stop_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.blocked_reason_normalized",
                    run_state.get("lifecycle_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.blocked_reasons_normalized",
                    ", ".join([str(v) for v in (run_state.get("lifecycle_blocked_reasons") or [])]),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_allowed_actions",
                    ", ".join([str(v) for v in run_state.get("loop_allowed_actions", [])]),
                )
            )
            rows.append(line("lifecycle.unit_blocked", run_state.get("unit_blocked")))
            rows.append(line("lifecycle.commit_execution_executed", run_state.get("commit_execution_executed")))
            rows.append(line("lifecycle.commit_execution_pending", run_state.get("commit_execution_pending")))
            rows.append(line("lifecycle.commit_execution_failed", run_state.get("commit_execution_failed")))
            rows.append(line("lifecycle.push_execution_succeeded", run_state.get("push_execution_succeeded")))
            rows.append(line("lifecycle.pr_execution_succeeded", run_state.get("pr_execution_succeeded")))
            rows.append(line("lifecycle.merge_execution_succeeded", run_state.get("merge_execution_succeeded")))
            rows.append(line("lifecycle.push_execution_pending", run_state.get("push_execution_pending")))
            rows.append(line("lifecycle.pr_execution_pending", run_state.get("pr_execution_pending")))
            rows.append(line("lifecycle.merge_execution_pending", run_state.get("merge_execution_pending")))
            rows.append(line("lifecycle.push_execution_failed", run_state.get("push_execution_failed")))
            rows.append(line("lifecycle.pr_execution_failed", run_state.get("pr_execution_failed")))
            rows.append(line("lifecycle.merge_execution_failed", run_state.get("merge_execution_failed")))
            rows.append(line("lifecycle.rollback_execution_attempted", run_state.get("rollback_execution_attempted")))
            rows.append(line("lifecycle.rollback_execution_succeeded", run_state.get("rollback_execution_succeeded")))
            rows.append(line("lifecycle.rollback_execution_pending", run_state.get("rollback_execution_pending")))
            rows.append(line("lifecycle.rollback_execution_failed", run_state.get("rollback_execution_failed")))
            rows.append(
                line(
                    "lifecycle.rollback_execution_manual_intervention_required",
                    run_state.get("rollback_execution_manual_intervention_required"),
                )
            )
            rows.append(line("lifecycle.rollback_replan_required", run_state.get("rollback_replan_required")))
            rows.append(
                line(
                    "lifecycle.rollback_automatic_continuation_blocked",
                    run_state.get("rollback_automatic_continuation_blocked"),
                )
            )
            rows.append(line("lifecycle.rollback_aftermath_status_run", run_state.get("rollback_aftermath_status")))
            rows.append(line("lifecycle.rollback_aftermath_blocked_run", run_state.get("rollback_aftermath_blocked")))
            rows.append(
                line(
                    "lifecycle.rollback_aftermath_manual_required_run",
                    run_state.get("rollback_aftermath_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_aftermath_missing_or_ambiguous_run",
                    run_state.get("rollback_aftermath_missing_or_ambiguous"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_aftermath_blocked_reason_run",
                    run_state.get("rollback_aftermath_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_manual_followup_required_run",
                    run_state.get("rollback_manual_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_remote_followup_required_run",
                    run_state.get("rollback_remote_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_validation_failed_run",
                    run_state.get("rollback_validation_failed"),
                )
            )
        if isinstance(paths, dict):
            rows.append(line("lifecycle.checkpoint_decision_path", paths.get("checkpoint_decision")))
            rows.append(line("lifecycle.commit_decision_path", paths.get("commit_decision")))
            rows.append(line("lifecycle.merge_decision_path", paths.get("merge_decision")))
            rows.append(line("lifecycle.rollback_decision_path", paths.get("rollback_decision")))
            rows.append(line("lifecycle.commit_execution_path", paths.get("commit_execution")))
            rows.append(line("lifecycle.push_execution_path", paths.get("push_execution")))
            rows.append(line("lifecycle.pr_execution_path", paths.get("pr_execution")))
            rows.append(line("lifecycle.merge_execution_path", paths.get("merge_execution")))
            rows.append(line("lifecycle.rollback_execution_path", paths.get("rollback_execution")))
            rows.append(line("lifecycle.run_state_path", paths.get("run_state")))

    paths = summary.get("paths", {})
    if isinstance(paths, dict):
        rows.append(line("request_path", paths.get("request")))
        rows.append(line("result_path", paths.get("result")))
        rows.append(line("rubric_path", paths.get("rubric")))
        rows.append(line("merge_gate_path", paths.get("merge_gate")))
        rows.append(line("classification_path", paths.get("classification")))

    body = "\n".join(rows)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "  <title>Operator Summary</title>\n"
        "  <style>\n"
        "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; "
        "margin: 0; padding: 16px; background: #f8fafc; color: #0f172a; }\n"
        "    .card { max-width: 760px; margin: 0 auto; background: #ffffff; border-radius: 12px; "
        "padding: 16px; box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08); }\n"
        "    h1 { margin: 0 0 12px; font-size: 20px; }\n"
        "    .row { display: grid; grid-template-columns: 160px 1fr; gap: 8px; "
        "padding: 8px 0; border-bottom: 1px solid #e2e8f0; }\n"
        "    .row:last-child { border-bottom: 0; }\n"
        "    .label { font-weight: 600; color: #334155; }\n"
        "    .value { overflow-wrap: anywhere; }\n"
        "    @media (max-width: 640px) {\n"
        "      .row { grid-template-columns: 1fr; gap: 4px; }\n"
        "      .label { font-size: 13px; }\n"
        "      .value { font-size: 14px; }\n"
        "    }\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        '  <div class="card">\n'
        "    <h1>Operator Summary</h1>\n"
        f"{body}\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.latest:
        row = get_latest_job(db_path=args.db_path)
        if row is None:
            print("No recorded jobs found in ledger.", file=sys.stderr)
            return 1
    else:
        row = get_job_by_id(args.job_id, db_path=args.db_path)
        if row is None:
            print(f"Job not found: {args.job_id}", file=sys.stderr)
            return 1

    summary = _build_summary(row, db_path=str(args.db_path))
    output_dir = _derive_output_dir(row, out_dir_arg=args.out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    job_id = str(summary.get("job_id", "unknown-job"))
    json_path = output_dir / f"{job_id}_operator_summary.json"
    html_path = output_dir / f"{job_id}_operator_summary.html"
    machine_payload_path = output_dir / f"{job_id}_machine_review_payload.json"

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    html_path.write_text(_to_html(summary), encoding="utf-8")
    machine_payload = _build_machine_review_payload(
        summary,
        summary_json_path=json_path,
        summary_html_path=html_path,
        machine_payload_path=machine_payload_path,
    )
    machine_payload_path.write_text(
        json.dumps(machine_payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    record_machine_review_payload_path(
        job_id=job_id,
        machine_review_payload_path=str(machine_payload_path.resolve()),
        db_path=args.db_path,
    )

    print(f"summary_json_path={json_path}")
    print(f"summary_html_path={html_path}")
    print(f"machine_review_payload_path={machine_payload_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

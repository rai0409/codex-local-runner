from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.ledger import DEFAULT_LEDGER_DB_PATH  # noqa: E402
from orchestrator.ledger import get_rollback_execution_by_job_id  # noqa: E402
from orchestrator.ledger import get_job_by_id  # noqa: E402
from orchestrator.ledger import get_latest_job  # noqa: E402
from orchestrator.ledger import get_rollback_trace_by_job_id  # noqa: E402
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface  # noqa: E402
from automation.orchestration.operator_explainability import build_operator_explainability_surface  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect a recorded orchestration job")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--job-id")
    selector.add_argument("--latest", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--db-path", default=DEFAULT_LEDGER_DB_PATH)
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


def _read_fail_reasons(path_value: Any) -> list[str]:
    if not isinstance(path_value, str) or not path_value.strip():
        return []
    path = Path(path_value)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    raw = payload.get("fail_reasons")
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(item) for item in raw]


def _read_json_object(path_value: Any) -> dict[str, Any] | None:
    if not isinstance(path_value, str) or not path_value.strip():
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


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

    checkpoint_payload = _read_json_object(str(checkpoint_path))
    commit_payload = _read_json_object(str(commit_path))
    merge_payload = _read_json_object(str(merge_path))
    rollback_payload = _read_json_object(str(rollback_path))
    commit_execution_payload = _read_json_object(str(commit_execution_path))
    push_execution_payload = _read_json_object(str(push_execution_path))
    pr_execution_payload = _read_json_object(str(pr_execution_path))
    merge_execution_payload = _read_json_object(str(merge_execution_path))
    rollback_execution_payload = _read_json_object(str(rollback_execution_path))
    run_state_payload = _read_json_object(str(run_state_path))

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


def _default_replan_input() -> dict[str, Any]:
    return {
        "failure_type": None,
        "current_state": None,
        "lifecycle_state": None,
        "write_authority_state": None,
        "category": None,
        "changed_files": [],
        "prior_attempt_count": None,
        "retry_budget_total": None,
        "retry_budget_remaining": None,
        "budget_exhausted": None,
        "primary_fail_reasons": [],
        "retry_recommendation": None,
        "next_action_readiness": None,
        "retry_recommended": None,
        "escalation_required": None,
        "retriable_failure_type": None,
        "retriable_failure_types": [],
    }


def _default_write_authority_surface() -> dict[str, Any]:
    return {
        "state": None,
        "allowed_categories": [],
    }


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _read_replan_input(path_value: Any) -> dict[str, Any]:
    payload = _read_json_object(path_value)
    if not isinstance(payload, dict):
        return _default_replan_input()

    raw = payload.get("replan_input")
    if not isinstance(raw, dict):
        return _default_replan_input()

    result = _default_replan_input()
    for key in (
        "failure_type",
        "current_state",
        "lifecycle_state",
        "write_authority_state",
        "category",
        "retry_recommendation",
        "next_action_readiness",
    ):
        if raw.get(key) is not None:
            text = str(raw.get(key)).strip()
            result[key] = text if text else None

    for key in (
        "prior_attempt_count",
        "retry_budget_total",
        "retry_budget_remaining",
    ):
        value = raw.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            result[key] = value
        elif isinstance(value, str) and value.strip().isdigit():
            result[key] = int(value.strip())

    for key in (
        "budget_exhausted",
        "retry_recommended",
        "escalation_required",
        "retriable_failure_type",
    ):
        result[key] = _as_optional_bool(raw.get(key))

    changed_files = raw.get("changed_files")
    if isinstance(changed_files, (list, tuple)):
        result["changed_files"] = [str(item) for item in changed_files]

    primary_fail_reasons = raw.get("primary_fail_reasons")
    if isinstance(primary_fail_reasons, (list, tuple)):
        result["primary_fail_reasons"] = [str(item) for item in primary_fail_reasons]

    retriable_failure_types = raw.get("retriable_failure_types")
    if isinstance(retriable_failure_types, (list, tuple)):
        result["retriable_failure_types"] = [str(item) for item in retriable_failure_types]

    return result


def _read_merge_gate_contract(
    path_value: Any,
    *,
    replan_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _read_json_object(path_value)
    normalized_replan = replan_input if isinstance(replan_input, dict) else _default_replan_input()

    lifecycle_state: str | None = None
    write_authority = _default_write_authority_surface()
    if isinstance(payload, dict):
        raw_lifecycle_state = payload.get("lifecycle_state")
        if raw_lifecycle_state is not None:
            text = str(raw_lifecycle_state).strip()
            lifecycle_state = text if text else None

        raw_write_authority = payload.get("write_authority")
        if isinstance(raw_write_authority, dict):
            raw_state = raw_write_authority.get("state")
            if raw_state is not None:
                text = str(raw_state).strip()
                write_authority["state"] = text if text else None
            write_authority["allowed_categories"] = _normalize_string_list(
                raw_write_authority.get("allowed_categories")
            )

    return {
        "lifecycle_state": lifecycle_state,
        "write_authority": write_authority,
        "failure_type": normalized_replan.get("failure_type"),
        "retry_recommended": _as_optional_bool(normalized_replan.get("retry_recommended")),
        "retry_recommendation": normalized_replan.get("retry_recommendation"),
        "retry_budget_remaining": normalized_replan.get("retry_budget_remaining"),
        "escalation_required": _as_optional_bool(normalized_replan.get("escalation_required")),
        "next_action_readiness": normalized_replan.get("next_action_readiness"),
        "primary_fail_reasons": _normalize_string_list(
            normalized_replan.get("primary_fail_reasons")
        ),
    }


def _read_retry_metadata(machine_review_payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(machine_review_payload, dict):
        return {
            "retry_recommended": None,
            "retry_basis": [],
            "retry_blockers": [],
        }

    raw = machine_review_payload.get("retry_metadata")
    if not isinstance(raw, dict):
        return {
            "retry_recommended": None,
            "retry_basis": [],
            "retry_blockers": [],
        }

    raw_retry_recommended = raw.get("retry_recommended")
    retry_recommended = (
        _as_optional_bool(raw_retry_recommended)
        if raw_retry_recommended is not None
        else None
    )
    raw_retry_basis = raw.get("retry_basis")
    retry_basis = (
        [str(item) for item in raw_retry_basis]
        if isinstance(raw_retry_basis, (list, tuple))
        else []
    )
    raw_retry_blockers = raw.get("retry_blockers")
    retry_blockers = (
        [str(item) for item in raw_retry_blockers]
        if isinstance(raw_retry_blockers, (list, tuple))
        else []
    )
    return {
        "retry_recommended": retry_recommended,
        "retry_basis": retry_basis,
        "retry_blockers": retry_blockers,
    }


def _read_recovery_policy(machine_review_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(machine_review_payload, dict):
        return None

    if isinstance(machine_review_payload.get("recovery_policy"), dict):
        return dict(machine_review_payload["recovery_policy"])

    required = (
        "score_total",
        "dimension_scores",
        "failure_codes",
        "recovery_decision",
        "decision_basis",
        "requires_human_review",
    )
    if not all(key in machine_review_payload for key in required):
        return None

    return {
        "score_total": machine_review_payload.get("score_total"),
        "dimension_scores": machine_review_payload.get("dimension_scores"),
        "failure_codes": machine_review_payload.get("failure_codes"),
        "recovery_decision": machine_review_payload.get("recovery_decision"),
        "decision_basis": machine_review_payload.get("decision_basis"),
        "requires_human_review": machine_review_payload.get("requires_human_review"),
    }


def _policy_reasons(machine_review_payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(machine_review_payload, dict):
        return []
    raw_policy_reasons = machine_review_payload.get("policy_reasons")
    if isinstance(raw_policy_reasons, (list, tuple)):
        return [str(item) for item in raw_policy_reasons]
    recovery_policy = _read_recovery_policy(machine_review_payload)
    if isinstance(recovery_policy, dict):
        raw_failure_codes = recovery_policy.get("failure_codes")
        if isinstance(raw_failure_codes, (list, tuple)):
            return [str(item) for item in raw_failure_codes]
    return []


def _display_recommendation(machine_review_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(machine_review_payload, dict):
        return None
    raw = machine_review_payload.get("recovery_decision")
    if raw is None:
        raw = machine_review_payload.get("recommended_action")
    normalized = str(raw).strip().lower() if raw is not None else ""
    if normalized in {
        "keep",
        "revise_current_state",
        "reset_and_retry",
        "escalate",
        "rollback",
        "retry",
    }:
        return normalized
    return None


def _derive_recommendation_advisory(
    machine_review_payload: dict[str, Any] | None,
    *,
    retry_metadata: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(machine_review_payload, dict):
        return {
            "display_recommendation": None,
            "decision_confidence": None,
            "operator_attention_flags": [],
            "execution_allowed": False,
        }

    display_recommendation = _display_recommendation(machine_review_payload)

    requires_human_review = _as_optional_bool(
        machine_review_payload.get("requires_human_review")
    )
    if requires_human_review is None:
        recovery_policy = _read_recovery_policy(machine_review_payload)
        if isinstance(recovery_policy, dict):
            requires_human_review = _as_optional_bool(
                recovery_policy.get("requires_human_review")
            )
    policy_reasons = _policy_reasons(machine_review_payload)
    retry_basis = [
        str(item) for item in retry_metadata.get("retry_basis", [])
    ] if isinstance(retry_metadata.get("retry_basis"), (list, tuple)) else []
    retry_blockers = [
        str(item) for item in retry_metadata.get("retry_blockers", [])
    ] if isinstance(retry_metadata.get("retry_blockers"), (list, tuple)) else []

    operator_attention_flags: list[str] = []
    for tag in [*policy_reasons, *retry_basis, *retry_blockers]:
        if tag and tag not in operator_attention_flags:
            operator_attention_flags.append(tag)

    decision_confidence: str | None
    if display_recommendation is None:
        decision_confidence = None
    elif requires_human_review is True:
        decision_confidence = "low"
    elif display_recommendation in {"retry", "reset_and_retry"}:
        retry_recommended = retry_metadata.get("retry_recommended")
        if retry_recommended is True:
            decision_confidence = "medium" if not retry_blockers else "low"
        elif retry_recommended is False:
            decision_confidence = "low"
        else:
            decision_confidence = None
    elif display_recommendation in {"keep", "rollback"}:
        decision_confidence = "medium"
    else:
        decision_confidence = "low"

    return {
        "display_recommendation": display_recommendation,
        "decision_confidence": decision_confidence,
        "operator_attention_flags": operator_attention_flags,
        "execution_allowed": False,
    }


def _derive_execution_bridge(
    machine_review_payload: dict[str, Any] | None,
    *,
    retry_metadata: dict[str, Any],
    advisory: dict[str, Any],
) -> dict[str, Any]:
    policy_reasons = _policy_reasons(machine_review_payload)

    retry_blockers = []
    raw_retry_blockers = retry_metadata.get("retry_blockers")
    if isinstance(raw_retry_blockers, (list, tuple)):
        retry_blockers = [str(item) for item in raw_retry_blockers]

    advisory_flags = []
    raw_advisory_flags = advisory.get("operator_attention_flags")
    if isinstance(raw_advisory_flags, (list, tuple)):
        advisory_flags = [str(item) for item in raw_advisory_flags]

    blockers: list[str] = []
    for tag in [*policy_reasons, *retry_blockers, *advisory_flags]:
        if tag and tag not in blockers:
            blockers.append(tag)

    # Current repository posture is explicitly human-gated and non-executing.
    for foundational_blocker in (
        "explicit_operator_gate_required",
        "execution_not_implemented",
    ):
        if foundational_blocker not in blockers:
            blockers.append(foundational_blocker)

    return {
        "eligible_for_bounded_execution": False,
        "eligibility_basis": [],
        "eligibility_blockers": blockers,
        "requires_explicit_operator_decision": True,
    }


def _derive_mode_visibility(
    *,
    machine_review_recorded: bool,
    advisory: dict[str, Any],
    execution_bridge: dict[str, Any],
) -> dict[str, Any]:
    mode_basis: list[str] = []
    if machine_review_recorded:
        mode_basis.append("ledger_backed_machine_review_visible")
    if execution_bridge.get("requires_explicit_operator_decision") is True:
        mode_basis.append("explicit_operator_decision_required")

    blockers: list[str] = []
    raw_bridge_blockers = execution_bridge.get("eligibility_blockers")
    if isinstance(raw_bridge_blockers, (list, tuple)):
        blockers.extend(str(item) for item in raw_bridge_blockers if str(item))

    raw_advisory_flags = advisory.get("operator_attention_flags")
    if isinstance(raw_advisory_flags, (list, tuple)):
        for item in raw_advisory_flags:
            tag = str(item)
            if tag and tag not in blockers:
                blockers.append(tag)

    for foundational_blocker in (
        "explicit_operator_gate_required",
        "execution_not_implemented",
    ):
        if foundational_blocker not in blockers:
            blockers.append(foundational_blocker)

    return {
        "current_mode": "manual_review_only",
        "next_possible_mode": None,
        "mode_basis": mode_basis,
        "mode_blockers": blockers,
    }


def _build_output(row: dict[str, Any], *, db_path: str) -> dict[str, Any]:
    rubric_path = row.get("rubric_path")
    merge_gate_path = row.get("merge_gate_path")
    replan_input = _read_replan_input(merge_gate_path)
    merge_gate_contract = _read_merge_gate_contract(
        merge_gate_path,
        replan_input=replan_input,
    )
    rollback_trace = get_rollback_trace_by_job_id(
        str(row.get("job_id", "")),
        db_path=db_path,
    )
    rollback_execution = get_rollback_execution_by_job_id(
        str(row.get("job_id", "")),
        db_path=db_path,
    )
    machine_review_payload_path_value = row.get("machine_review_payload_path")
    machine_review_payload_path = (
        str(machine_review_payload_path_value).strip()
        if isinstance(machine_review_payload_path_value, str)
        else ""
    )
    machine_review_recorded = machine_review_payload_path != ""
    machine_review_payload = (
        _read_json_object(machine_review_payload_path)
        if machine_review_recorded
        else None
    )
    retry_metadata = _read_retry_metadata(machine_review_payload)
    advisory = _derive_recommendation_advisory(
        machine_review_payload,
        retry_metadata=retry_metadata,
    )
    execution_bridge = _derive_execution_bridge(
        machine_review_payload,
        retry_metadata=retry_metadata,
        advisory=advisory,
    )
    mode_visibility = _derive_mode_visibility(
        machine_review_recorded=machine_review_recorded,
        advisory=advisory,
        execution_bridge=execution_bridge,
    )
    recovery_policy = _read_recovery_policy(machine_review_payload)
    recovery_decision = (
        machine_review_payload.get("recovery_decision")
        if machine_review_payload is not None
        else None
    )
    if recovery_decision is None and recovery_policy is not None:
        recovery_decision = recovery_policy.get("recovery_decision")
    recommended_action = (
        machine_review_payload.get("recommended_action")
        if machine_review_payload is not None
        else None
    )
    if recommended_action is None:
        recommended_action = recovery_decision
    failure_codes = []
    if machine_review_payload is not None:
        raw_failure_codes = machine_review_payload.get("failure_codes")
        if isinstance(raw_failure_codes, (list, tuple)):
            failure_codes = [str(item) for item in raw_failure_codes]
    if not failure_codes and isinstance(recovery_policy, dict):
        nested_failure_codes = recovery_policy.get("failure_codes")
        if isinstance(nested_failure_codes, (list, tuple)):
            failure_codes = [str(item) for item in nested_failure_codes]
    decision_basis = []
    if machine_review_payload is not None:
        raw_decision_basis = machine_review_payload.get("decision_basis")
        if isinstance(raw_decision_basis, (list, tuple)):
            decision_basis = [str(item) for item in raw_decision_basis]
    if not decision_basis and isinstance(recovery_policy, dict):
        nested_decision_basis = recovery_policy.get("decision_basis")
        if isinstance(nested_decision_basis, (list, tuple)):
            decision_basis = [str(item) for item in nested_decision_basis]
    lifecycle_artifacts = _read_lifecycle_artifacts(row.get("result_path"))
    return {
        "job_id": row.get("job_id"),
        "repo": row.get("repo"),
        "task_type": row.get("task_type"),
        "provider": row.get("provider"),
        "accepted_status": row.get("accepted_status"),
        "declared_category": row.get("declared_category"),
        "observed_category": row.get("observed_category"),
        "merge_eligible": _as_optional_bool(row.get("merge_eligible")),
        "merge_gate_passed": _as_optional_bool(row.get("merge_gate_passed")),
        "created_at": row.get("created_at"),
        "paths": {
            "request": row.get("request_path"),
            "result": row.get("result_path"),
            "rubric": rubric_path,
            "merge_gate": merge_gate_path,
            "machine_review_payload": (
                machine_review_payload_path
                if machine_review_recorded
                else None
            ),
        },
        "fail_reasons": {
            "rubric": _read_fail_reasons(rubric_path),
            "merge_gate": _read_fail_reasons(merge_gate_path),
        },
        "lifecycle_state": merge_gate_contract["lifecycle_state"],
        "write_authority": merge_gate_contract["write_authority"],
        "failure_type": merge_gate_contract["failure_type"],
        "retry_recommended": merge_gate_contract["retry_recommended"],
        "retry_recommendation": merge_gate_contract["retry_recommendation"],
        "retry_budget_remaining": merge_gate_contract["retry_budget_remaining"],
        "escalation_required": merge_gate_contract["escalation_required"],
        "next_action_readiness": merge_gate_contract["next_action_readiness"],
        "primary_fail_reasons": merge_gate_contract["primary_fail_reasons"],
        "replan_input": replan_input,
        "rollback_trace": {
            "recorded": rollback_trace is not None,
            "rollback_trace_id": rollback_trace.get("rollback_trace_id") if rollback_trace else None,
            "rollback_eligible": (
                _as_optional_bool(rollback_trace.get("rollback_eligible"))
                if rollback_trace
                else None
            ),
            "ineligible_reason": rollback_trace.get("ineligible_reason") if rollback_trace else None,
            "pre_merge_sha": rollback_trace.get("pre_merge_sha") if rollback_trace else None,
            "post_merge_sha": rollback_trace.get("post_merge_sha") if rollback_trace else None,
        },
        "rollback_execution": {
            "recorded": rollback_execution is not None,
            "status": rollback_execution.get("execution_status") if rollback_execution else None,
            "attempted_at": rollback_execution.get("attempted_at") if rollback_execution else None,
            "rollback_result_sha": (
                rollback_execution.get("rollback_result_sha") if rollback_execution else None
            ),
            "rollback_error": rollback_execution.get("rollback_error") if rollback_execution else None,
        },
        "machine_review": {
            "recorded": machine_review_recorded,
            "recommended_action": recommended_action,
            "recovery_decision": recovery_decision,
            "policy_version": (
                machine_review_payload.get("policy_version")
                if machine_review_payload is not None
                else None
            ),
            "policy_reasons": _policy_reasons(machine_review_payload),
            "score_total": (
                machine_review_payload.get("score_total")
                if machine_review_payload is not None
                else None
            ),
            "dimension_scores": (
                machine_review_payload.get("dimension_scores")
                if machine_review_payload is not None
                else None
            ),
            "failure_codes": (
                failure_codes
            ),
            "decision_basis": (
                decision_basis
            ),
            "requires_human_review": (
                _as_optional_bool(machine_review_payload.get("requires_human_review"))
                if machine_review_payload is not None
                else None
            ),
            "recovery_policy": recovery_policy,
            "retry_metadata": retry_metadata,
            "advisory": advisory,
            "execution_bridge": execution_bridge,
            "mode_visibility": mode_visibility,
        },
        "lifecycle_artifacts": lifecycle_artifacts,
    }


def _fmt(value: Any) -> str:
    if value is None:
        return "<missing>"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _format_human(output: dict[str, Any]) -> str:
    lines = [
        f"job_id: {_fmt(output.get('job_id'))}",
        f"repo: {_fmt(output.get('repo'))}",
        f"task_type: {_fmt(output.get('task_type'))}",
        f"provider: {_fmt(output.get('provider'))}",
        f"accepted_status: {_fmt(output.get('accepted_status'))}",
        f"declared_category: {_fmt(output.get('declared_category'))}",
        f"observed_category: {_fmt(output.get('observed_category'))}",
        f"merge_eligible: {_fmt(output.get('merge_eligible'))}",
        f"merge_gate_passed: {_fmt(output.get('merge_gate_passed'))}",
        f"created_at: {_fmt(output.get('created_at'))}",
        f"request_path: {_fmt(output['paths'].get('request'))}",
        f"result_path: {_fmt(output['paths'].get('result'))}",
        f"rubric_path: {_fmt(output['paths'].get('rubric'))}",
        f"merge_gate_path: {_fmt(output['paths'].get('merge_gate'))}",
        f"machine_review_payload_path: {_fmt(output['paths'].get('machine_review_payload'))}",
        "rubric_fail_reasons: "
        + (", ".join(output["fail_reasons"]["rubric"]) if output["fail_reasons"]["rubric"] else "none"),
        "merge_gate_fail_reasons: "
        + (
            ", ".join(output["fail_reasons"]["merge_gate"])
            if output["fail_reasons"]["merge_gate"]
            else "none"
        ),
        f"lifecycle_state: {_fmt(output.get('lifecycle_state'))}",
        f"write_authority_state: {_fmt(output['write_authority'].get('state'))}",
        "write_authority_allowed_categories: "
        + (
            ", ".join([str(v) for v in output["write_authority"].get("allowed_categories", [])])
            if output["write_authority"].get("allowed_categories")
            else "none"
        ),
        f"failure_type: {_fmt(output.get('failure_type'))}",
        f"retry_recommended: {_fmt(output.get('retry_recommended'))}",
        f"retry_recommendation: {_fmt(output.get('retry_recommendation'))}",
        f"retry_budget_remaining: {_fmt(output.get('retry_budget_remaining'))}",
        f"escalation_required: {_fmt(output.get('escalation_required'))}",
        f"next_action_readiness: {_fmt(output.get('next_action_readiness'))}",
        "primary_fail_reasons: "
        + (
            ", ".join([str(v) for v in output.get("primary_fail_reasons", [])])
            if output.get("primary_fail_reasons")
            else "none"
        ),
        f"rollback_trace_recorded: {_fmt(output['rollback_trace'].get('recorded'))}",
        f"rollback_eligible: {_fmt(output['rollback_trace'].get('rollback_eligible'))}",
        f"rollback_ineligible_reason: {_fmt(output['rollback_trace'].get('ineligible_reason'))}",
        f"rollback_pre_merge_sha: {_fmt(output['rollback_trace'].get('pre_merge_sha'))}",
        f"rollback_post_merge_sha: {_fmt(output['rollback_trace'].get('post_merge_sha'))}",
        f"rollback_execution_recorded: {_fmt(output['rollback_execution'].get('recorded'))}",
        f"rollback_execution_status: {_fmt(output['rollback_execution'].get('status'))}",
        f"rollback_result_sha: {_fmt(output['rollback_execution'].get('rollback_result_sha'))}",
        f"rollback_error: {_fmt(output['rollback_execution'].get('rollback_error'))}",
        f"machine_review_recorded: {_fmt(output['machine_review'].get('recorded'))}",
        f"recommended_action: {_fmt(output['machine_review'].get('recommended_action'))}",
        f"recovery_decision: {_fmt(output['machine_review'].get('recovery_decision'))}",
        f"policy_version: {_fmt(output['machine_review'].get('policy_version'))}",
        f"score_total: {_fmt(output['machine_review'].get('score_total'))}",
        "dimension_scores: "
        + (
            json.dumps(output["machine_review"].get("dimension_scores"), ensure_ascii=False, sort_keys=True)
            if output["machine_review"].get("dimension_scores") is not None
            else "<missing>"
        ),
        "failure_codes: "
        + (
            ", ".join([str(v) for v in output["machine_review"].get("failure_codes", [])])
            if output["machine_review"].get("failure_codes")
            else "none"
        ),
        "decision_basis: "
        + (
            ", ".join([str(v) for v in output["machine_review"].get("decision_basis", [])])
            if output["machine_review"].get("decision_basis")
            else "none"
        ),
        "policy_reasons: "
        + (
            ", ".join([str(v) for v in output["machine_review"].get("policy_reasons", [])])
            if output["machine_review"].get("policy_reasons")
            else "none"
        ),
        f"requires_human_review: {_fmt(output['machine_review'].get('requires_human_review'))}",
        f"retry_recommended: {_fmt(output['machine_review']['retry_metadata'].get('retry_recommended'))}",
        "retry_basis: "
        + (
            ", ".join(
                [str(v) for v in output["machine_review"]["retry_metadata"].get("retry_basis", [])]
            )
            if output["machine_review"]["retry_metadata"].get("retry_basis")
            else "none"
        ),
        "retry_blockers: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["retry_metadata"].get(
                        "retry_blockers", []
                    )
                ]
            )
            if output["machine_review"]["retry_metadata"].get("retry_blockers")
            else "none"
        ),
        f"advisory_display_recommendation: {_fmt(output['machine_review']['advisory'].get('display_recommendation'))}",
        f"advisory_decision_confidence: {_fmt(output['machine_review']['advisory'].get('decision_confidence'))}",
        "advisory_attention_flags: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["advisory"].get(
                        "operator_attention_flags", []
                    )
                ]
            )
            if output["machine_review"]["advisory"].get("operator_attention_flags")
            else "none"
        ),
        f"advisory_execution_allowed: {_fmt(output['machine_review']['advisory'].get('execution_allowed'))}",
        "execution_bridge_eligible_for_bounded_execution: "
        + _fmt(output["machine_review"]["execution_bridge"].get("eligible_for_bounded_execution")),
        "execution_bridge_eligibility_basis: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["execution_bridge"].get(
                        "eligibility_basis", []
                    )
                ]
            )
            if output["machine_review"]["execution_bridge"].get("eligibility_basis")
            else "none"
        ),
        "execution_bridge_eligibility_blockers: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["execution_bridge"].get(
                        "eligibility_blockers", []
                    )
                ]
            )
            if output["machine_review"]["execution_bridge"].get("eligibility_blockers")
            else "none"
        ),
        "execution_bridge_requires_explicit_operator_decision: "
        + _fmt(
            output["machine_review"]["execution_bridge"].get(
                "requires_explicit_operator_decision"
            )
        ),
        f"mode_visibility_current_mode: {_fmt(output['machine_review']['mode_visibility'].get('current_mode'))}",
        f"mode_visibility_next_possible_mode: {_fmt(output['machine_review']['mode_visibility'].get('next_possible_mode'))}",
        "mode_visibility_mode_basis: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["mode_visibility"].get(
                        "mode_basis", []
                    )
                ]
            )
            if output["machine_review"]["mode_visibility"].get("mode_basis")
            else "none"
        ),
        "mode_visibility_mode_blockers: "
        + (
            ", ".join(
                [
                    str(v)
                    for v in output["machine_review"]["mode_visibility"].get(
                        "mode_blockers", []
                    )
                ]
            )
            if output["machine_review"]["mode_visibility"].get("mode_blockers")
            else "none"
        ),
        f"lifecycle_checkpoint_stage: {_fmt(output['lifecycle_artifacts']['checkpoint_decision'].get('checkpoint_stage'))}",
        f"lifecycle_checkpoint_decision: {_fmt(output['lifecycle_artifacts']['checkpoint_decision'].get('decision'))}",
        f"lifecycle_checkpoint_manual_intervention_required: {_fmt(output['lifecycle_artifacts']['checkpoint_decision'].get('manual_intervention_required'))}",
        f"lifecycle_checkpoint_global_stop_recommended: {_fmt(output['lifecycle_artifacts']['checkpoint_decision'].get('global_stop_recommended'))}",
        f"lifecycle_commit_decision: {_fmt(output['lifecycle_artifacts']['commit_decision'].get('decision'))}",
        f"lifecycle_merge_decision: {_fmt(output['lifecycle_artifacts']['merge_decision'].get('decision'))}",
        f"lifecycle_rollback_decision: {_fmt(output['lifecycle_artifacts']['rollback_decision'].get('decision'))}",
        f"lifecycle_commit_execution_status: {_fmt(output['lifecycle_artifacts']['commit_execution'].get('status'))}",
        f"lifecycle_commit_execution_commit_sha: {_fmt(output['lifecycle_artifacts']['commit_execution'].get('commit_sha'))}",
        "lifecycle_commit_execution_manual_intervention_required: "
        + _fmt(output["lifecycle_artifacts"]["commit_execution"].get("manual_intervention_required")),
        "lifecycle_commit_execution_authority_status: "
        + _fmt(output["lifecycle_artifacts"]["commit_execution"].get("execution_authority_status")),
        "lifecycle_commit_execution_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["commit_execution"].get("validation_status")),
        f"lifecycle_push_execution_status: {_fmt(output['lifecycle_artifacts']['push_execution'].get('status'))}",
        f"lifecycle_push_execution_branch_name: {_fmt(output['lifecycle_artifacts']['push_execution'].get('branch_name'))}",
        "lifecycle_push_execution_authority_status: "
        + _fmt(output["lifecycle_artifacts"]["push_execution"].get("execution_authority_status")),
        "lifecycle_push_execution_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["push_execution"].get("validation_status")),
        "lifecycle_push_remote_state_status: "
        + _fmt(output["lifecycle_artifacts"]["push_execution"].get("remote_state_status")),
        "lifecycle_push_remote_state_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["push_execution"].get("remote_state_blocked_reason")),
        f"lifecycle_pr_execution_status: {_fmt(output['lifecycle_artifacts']['pr_execution'].get('status'))}",
        f"lifecycle_pr_execution_pr_number: {_fmt(output['lifecycle_artifacts']['pr_execution'].get('pr_number'))}",
        "lifecycle_pr_execution_authority_status: "
        + _fmt(output["lifecycle_artifacts"]["pr_execution"].get("execution_authority_status")),
        "lifecycle_pr_execution_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["pr_execution"].get("validation_status")),
        "lifecycle_pr_existing_pr_status: "
        + _fmt(output["lifecycle_artifacts"]["pr_execution"].get("existing_pr_status")),
        "lifecycle_pr_creation_state_status: "
        + _fmt(output["lifecycle_artifacts"]["pr_execution"].get("pr_creation_state_status")),
        "lifecycle_pr_remote_state_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["pr_execution"].get("remote_state_blocked_reason")),
        f"lifecycle_merge_execution_status: {_fmt(output['lifecycle_artifacts']['merge_execution'].get('status'))}",
        f"lifecycle_merge_execution_merge_commit_sha: {_fmt(output['lifecycle_artifacts']['merge_execution'].get('merge_commit_sha'))}",
        "lifecycle_merge_execution_authority_status: "
        + _fmt(output["lifecycle_artifacts"]["merge_execution"].get("execution_authority_status")),
        "lifecycle_merge_execution_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["merge_execution"].get("validation_status")),
        "lifecycle_merge_mergeability_status: "
        + _fmt(output["lifecycle_artifacts"]["merge_execution"].get("mergeability_status")),
        "lifecycle_merge_merge_requirements_status: "
        + _fmt(output["lifecycle_artifacts"]["merge_execution"].get("merge_requirements_status")),
        "lifecycle_merge_required_checks_status: "
        + _fmt(output["lifecycle_artifacts"]["merge_execution"].get("required_checks_status")),
        "lifecycle_merge_remote_state_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["merge_execution"].get("remote_state_blocked_reason")),
        f"lifecycle_rollback_execution_status: {_fmt(output['lifecycle_artifacts']['rollback_execution'].get('status'))}",
        f"lifecycle_rollback_execution_mode: {_fmt(output['lifecycle_artifacts']['rollback_execution'].get('rollback_mode'))}",
        "lifecycle_rollback_execution_resulting_commit_sha: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("resulting_commit_sha")),
        "lifecycle_rollback_execution_manual_intervention_required: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("manual_intervention_required")),
        "lifecycle_rollback_execution_authority_status: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("execution_authority_status")),
        "lifecycle_rollback_execution_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("validation_status")),
        "lifecycle_rollback_execution_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("replan_required")),
        "lifecycle_rollback_aftermath_status: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_aftermath_status")),
        "lifecycle_rollback_aftermath_blocked: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_aftermath_blocked")),
        "lifecycle_rollback_aftermath_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_aftermath_blocked_reason")),
        "lifecycle_rollback_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_validation_status")),
        "lifecycle_rollback_manual_followup_required: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_manual_followup_required")),
        "lifecycle_rollback_remote_followup_required: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_remote_followup_required")),
        "lifecycle_rollback_post_validation_status: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_post_validation_status")),
        "lifecycle_rollback_remote_state_status: "
        + _fmt(output["lifecycle_artifacts"]["rollback_execution"].get("rollback_remote_state_status")),
        f"lifecycle_run_state: {_fmt(output['lifecycle_artifacts']['run_state'].get('state'))}",
        "lifecycle_orchestration_state: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("orchestration_state")),
        f"lifecycle_global_stop: {_fmt(output['lifecycle_artifacts']['run_state'].get('global_stop'))}",
        f"lifecycle_continue_allowed: {_fmt(output['lifecycle_artifacts']['run_state'].get('continue_allowed'))}",
        f"lifecycle_run_paused: {_fmt(output['lifecycle_artifacts']['run_state'].get('run_paused'))}",
        "lifecycle_manual_intervention_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("manual_intervention_required")),
        "lifecycle_rollback_evaluation_pending: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_evaluation_pending")),
        "lifecycle_global_stop_recommended: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("global_stop_recommended")),
        "lifecycle_next_run_action: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("next_run_action")),
        "lifecycle_loop_state: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_state")),
        "lifecycle_next_safe_action: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("next_safe_action")),
        "lifecycle_loop_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_blocked_reason")),
        "lifecycle_loop_blocked_reasons: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("loop_blocked_reasons", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("loop_blocked_reasons")
            else "none"
        ),
        "lifecycle_resumable: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("resumable")),
        "lifecycle_terminal: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("terminal")),
        "lifecycle_loop_manual_intervention_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_manual_intervention_required")),
        "lifecycle_loop_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_replan_required")),
        "lifecycle_rollback_completed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_completed")),
        "lifecycle_delivery_completed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("delivery_completed")),
        "lifecycle_loop_allowed_actions: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("loop_allowed_actions", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("loop_allowed_actions")
            else "none"
        ),
        f"lifecycle_unit_blocked: {_fmt(output['lifecycle_artifacts']['run_state'].get('unit_blocked'))}",
        "lifecycle_commit_execution_executed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("commit_execution_executed")),
        "lifecycle_commit_execution_pending: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("commit_execution_pending")),
        "lifecycle_commit_execution_failed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("commit_execution_failed")),
        "lifecycle_push_execution_succeeded: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("push_execution_succeeded")),
        "lifecycle_pr_execution_succeeded: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("pr_execution_succeeded")),
        "lifecycle_merge_execution_succeeded: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("merge_execution_succeeded")),
        "lifecycle_push_execution_pending: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("push_execution_pending")),
        "lifecycle_pr_execution_pending: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("pr_execution_pending")),
        "lifecycle_merge_execution_pending: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("merge_execution_pending")),
        "lifecycle_push_execution_failed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("push_execution_failed")),
        "lifecycle_pr_execution_failed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("pr_execution_failed")),
        "lifecycle_merge_execution_failed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("merge_execution_failed")),
        "lifecycle_delivery_execution_manual_intervention_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("delivery_execution_manual_intervention_required")),
        "lifecycle_rollback_execution_attempted: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_execution_attempted")),
        "lifecycle_rollback_execution_succeeded: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_execution_succeeded")),
        "lifecycle_rollback_execution_pending: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_execution_pending")),
        "lifecycle_rollback_execution_failed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_execution_failed")),
        "lifecycle_rollback_execution_manual_intervention_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_execution_manual_intervention_required")),
        "lifecycle_rollback_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_replan_required")),
        "lifecycle_rollback_automatic_continuation_blocked: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_automatic_continuation_blocked")),
        "lifecycle_rollback_aftermath_status_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_aftermath_status")),
        "lifecycle_rollback_aftermath_blocked_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_aftermath_blocked")),
        "lifecycle_rollback_aftermath_manual_required_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_aftermath_manual_required")),
        "lifecycle_rollback_aftermath_missing_or_ambiguous_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_aftermath_missing_or_ambiguous")),
        "lifecycle_rollback_aftermath_blocked_reason_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_aftermath_blocked_reason")),
        "lifecycle_rollback_manual_followup_required_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_manual_followup_required")),
        "lifecycle_rollback_remote_followup_required_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_remote_followup_required")),
        "lifecycle_rollback_validation_failed_run: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_validation_failed")),
        "lifecycle_authority_validation_blocked: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("authority_validation_blocked")),
        "lifecycle_execution_authority_blocked: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authority_blocked")),
        "lifecycle_validation_blocked: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("validation_blocked")),
        "lifecycle_authority_validation_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("authority_validation_manual_required")),
        "lifecycle_authority_validation_missing_or_ambiguous: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("authority_validation_missing_or_ambiguous")),
        "lifecycle_authority_validation_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("authority_validation_blocked_reason")),
        "lifecycle_remote_github_blocked: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("remote_github_blocked")),
        "lifecycle_remote_github_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("remote_github_manual_required")),
        "lifecycle_remote_github_missing_or_ambiguous: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("remote_github_missing_or_ambiguous")),
        "lifecycle_remote_github_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("remote_github_blocked_reason")),
        "lifecycle_policy_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_status")),
        "lifecycle_policy_blocked: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_blocked")),
        "lifecycle_policy_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_manual_required")),
        "lifecycle_policy_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_replan_required")),
        "lifecycle_policy_resume_allowed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_resume_allowed")),
        "lifecycle_policy_terminal: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_terminal")),
        "lifecycle_policy_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_blocked_reason")),
        "lifecycle_policy_blocked_reasons: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("policy_blocked_reasons", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("policy_blocked_reasons")
            else "none"
        ),
        "lifecycle_policy_primary_blocker_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_primary_blocker_class")),
        "lifecycle_policy_primary_action: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_primary_action")),
        "lifecycle_policy_allowed_actions: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("policy_allowed_actions", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("policy_allowed_actions")
            else "none"
        ),
        "lifecycle_policy_disallowed_actions: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("policy_disallowed_actions", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("policy_disallowed_actions")
            else "none"
        ),
        "lifecycle_policy_manual_actions: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("policy_manual_actions", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("policy_manual_actions")
            else "none"
        ),
        "lifecycle_policy_resumable_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("policy_resumable_reason")),
        "lifecycle_operator_posture_summary: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_posture_summary")),
        "lifecycle_operator_primary_blocker_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_primary_blocker_class")),
        "lifecycle_operator_primary_action: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_primary_action")),
        "lifecycle_operator_action_scope: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_action_scope")),
        "lifecycle_operator_resume_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_resume_status")),
        "lifecycle_operator_next_safe_posture: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_next_safe_posture")),
        "lifecycle_operator_guidance_summary: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_guidance_summary")),
        "lifecycle_operator_safe_actions_summary: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_safe_actions_summary")),
        "lifecycle_operator_unsafe_actions_summary: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_unsafe_actions_summary")),
        "lifecycle_closure_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_closure_status")),
        "lifecycle_safely_closed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_safely_closed")),
        "lifecycle_terminal_normalized: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_terminal")),
        "lifecycle_resumable_normalized: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_resumable")),
        "lifecycle_manual_required_normalized: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_manual_required")),
        "lifecycle_replan_required_normalized: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_replan_required")),
        "lifecycle_execution_complete_not_closed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_execution_complete_not_closed")),
        "lifecycle_rollback_complete_not_closed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_rollback_complete_not_closed")),
        "lifecycle_primary_closure_issue: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_primary_closure_issue")),
        "lifecycle_stop_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_stop_class")),
        "lifecycle_blocked_reason_normalized: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lifecycle_blocked_reason")),
        "lifecycle_blocked_reasons_normalized: "
        + (
            ", ".join(
                [str(v) for v in output["lifecycle_artifacts"]["run_state"].get("lifecycle_blocked_reasons", [])]
            )
            if output["lifecycle_artifacts"]["run_state"].get("lifecycle_blocked_reasons")
            else "none"
        ),
        "lifecycle_global_stop_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("global_stop_reason")),
        f"lifecycle_checkpoint_decision_path: {_fmt(output['lifecycle_artifacts']['paths'].get('checkpoint_decision'))}",
        f"lifecycle_commit_decision_path: {_fmt(output['lifecycle_artifacts']['paths'].get('commit_decision'))}",
        f"lifecycle_merge_decision_path: {_fmt(output['lifecycle_artifacts']['paths'].get('merge_decision'))}",
        f"lifecycle_rollback_decision_path: {_fmt(output['lifecycle_artifacts']['paths'].get('rollback_decision'))}",
        f"lifecycle_commit_execution_path: {_fmt(output['lifecycle_artifacts']['paths'].get('commit_execution'))}",
        f"lifecycle_push_execution_path: {_fmt(output['lifecycle_artifacts']['paths'].get('push_execution'))}",
        f"lifecycle_pr_execution_path: {_fmt(output['lifecycle_artifacts']['paths'].get('pr_execution'))}",
        f"lifecycle_merge_execution_path: {_fmt(output['lifecycle_artifacts']['paths'].get('merge_execution'))}",
        f"lifecycle_rollback_execution_path: {_fmt(output['lifecycle_artifacts']['paths'].get('rollback_execution'))}",
        f"lifecycle_run_state_path: {_fmt(output['lifecycle_artifacts']['paths'].get('run_state'))}",
    ]
    return "\n".join(lines)


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

    output = _build_output(row, db_path=str(args.db_path))
    if args.as_json:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    else:
        print(_format_human(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

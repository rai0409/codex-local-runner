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
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface  # noqa: E402
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface  # noqa: E402
from automation.orchestration.bounded_execution_bridge import (  # noqa: E402
    build_bounded_execution_bridge_run_state_summary_surface,
)
from automation.orchestration.execution_authorization_gate import (
    build_execution_authorization_gate_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.execution_result_contract import (
    build_execution_result_contract_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.observability_rollup import (
    build_observability_rollup_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.artifact_retention import (
    build_artifact_retention_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_run_state_summary_surface,
)  # noqa: E402
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface  # noqa: E402
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface  # noqa: E402
from automation.orchestration.operator_explainability import build_operator_explainability_surface  # noqa: E402
from automation.orchestration.repair_approval_binding import build_repair_approval_binding_run_state_summary_surface  # noqa: E402
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_run_state_summary_surface  # noqa: E402
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_run_state_summary_surface  # noqa: E402
from automation.orchestration.reconcile_contract import build_reconcile_run_state_summary_surface  # noqa: E402


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
    objective_surface = build_objective_run_state_summary_surface(run_state)
    lifecycle_surface = build_lifecycle_terminal_state_surface({**run_state, **objective_surface})
    completion_surface = build_completion_run_state_summary_surface(
        {**run_state, **objective_surface, **lifecycle_surface}
    )
    approval_surface = build_approval_run_state_summary_surface(
        {**run_state, **objective_surface, **lifecycle_surface, **completion_surface}
    )
    reconcile_surface = build_reconcile_run_state_summary_surface(
        {**run_state, **objective_surface, **lifecycle_surface, **completion_surface, **approval_surface}
    )
    repair_surface = build_repair_suggestion_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
        }
    )
    repair_plan_surface = build_repair_plan_transport_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **repair_surface,
        }
    )
    repair_binding_surface = build_repair_approval_binding_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **repair_surface,
            **repair_plan_surface,
        }
    )
    execution_authorization_surface = build_execution_authorization_gate_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **repair_surface,
            **repair_plan_surface,
            **repair_binding_surface,
        }
    )
    bounded_execution_surface = build_bounded_execution_bridge_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **repair_surface,
            **repair_plan_surface,
            **repair_binding_surface,
            **execution_authorization_surface,
        }
    )
    execution_result_surface = build_execution_result_contract_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **repair_surface,
            **repair_plan_surface,
            **repair_binding_surface,
            **execution_authorization_surface,
            **bounded_execution_surface,
        }
    )
    verification_closure_surface = build_verification_closure_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **execution_authorization_surface,
            **bounded_execution_surface,
            **execution_result_surface,
        }
    )
    retry_reentry_surface = build_retry_reentry_loop_run_state_summary_surface(
        {
            **run_state,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **repair_surface,
            **repair_plan_surface,
            **repair_binding_surface,
            **execution_authorization_surface,
            **bounded_execution_surface,
            **execution_result_surface,
            **verification_closure_surface,
        }
    )
    endgame_surface = build_endgame_closure_run_state_summary_surface(
        {
            **run_state,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **execution_authorization_surface,
            **bounded_execution_surface,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
        }
    )
    loop_hardening_surface = build_loop_hardening_run_state_summary_surface(
        {
            **run_state,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
            **endgame_surface,
        }
    )
    lane_stabilization_surface = build_lane_stabilization_run_state_summary_surface(
        {
            **run_state,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **execution_authorization_surface,
            **bounded_execution_surface,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
            **endgame_surface,
            **loop_hardening_surface,
        }
    )
    observability_surface = build_observability_rollup_run_state_summary_surface(
        {
            **run_state,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
            **endgame_surface,
            **loop_hardening_surface,
            **lane_stabilization_surface,
        }
    )
    failure_bucketing_hardening_surface = (
        build_failure_bucketing_hardening_run_state_summary_surface(
            {
                **run_state,
                **loop_hardening_surface,
                **observability_surface,
            }
        )
    )
    artifact_retention_surface = build_artifact_retention_run_state_summary_surface(
        {
            **run_state,
            **failure_bucketing_hardening_surface,
        }
    )
    fleet_safety_surface = build_fleet_safety_control_run_state_summary_surface(
        {
            **run_state,
            **observability_surface,
            **failure_bucketing_hardening_surface,
            **lane_stabilization_surface,
            **loop_hardening_surface,
            **endgame_surface,
            **retry_reentry_surface,
            **artifact_retention_surface,
        }
    )
    merged = {
        **run_state,
        **objective_surface,
        **lifecycle_surface,
        **completion_surface,
        **approval_surface,
        **reconcile_surface,
        **repair_surface,
        **repair_plan_surface,
        **repair_binding_surface,
        **execution_authorization_surface,
        **bounded_execution_surface,
        **execution_result_surface,
        **verification_closure_surface,
        **retry_reentry_surface,
        **endgame_surface,
        **loop_hardening_surface,
        **lane_stabilization_surface,
        **observability_surface,
        **failure_bucketing_hardening_surface,
        **artifact_retention_surface,
        **fleet_safety_surface,
    }
    return {
        **merged,
        **build_operator_explainability_surface(
            merged,
            include_rendering_details=True,
        ),
    }


def _extract_objective_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "objective_id": None,
            "objective_summary": None,
            "objective_type": None,
            "requested_outcome": None,
            "objective_status": None,
            "objective_source_status": None,
            "acceptance_status": None,
            "scope_status": None,
            "required_artifacts_status": None,
            "objective_contract_blocked_reason": None,
            "acceptance_criteria_total": 0,
            "acceptance_criteria_defined": 0,
            "required_artifacts_total": 0,
        }

    acceptance_criteria = payload.get("acceptance_criteria")
    criteria = acceptance_criteria if isinstance(acceptance_criteria, list) else []
    required_artifacts = payload.get("required_artifacts")
    artifacts = required_artifacts if isinstance(required_artifacts, list) else []
    defined_count = 0
    for item in criteria:
        if isinstance(item, dict) and str(item.get("status", "")).strip() == "defined":
            defined_count += 1

    return {
        "schema_version": payload.get("schema_version"),
        "objective_id": payload.get("objective_id"),
        "objective_summary": payload.get("objective_summary"),
        "objective_type": payload.get("objective_type"),
        "requested_outcome": payload.get("requested_outcome"),
        "objective_status": payload.get("objective_status"),
        "objective_source_status": payload.get("objective_source_status"),
        "acceptance_status": payload.get("acceptance_status"),
        "scope_status": payload.get("scope_status"),
        "required_artifacts_status": payload.get("required_artifacts_status"),
        "objective_contract_blocked_reason": payload.get("objective_blocked_reason"),
        "acceptance_criteria_total": len(criteria),
        "acceptance_criteria_defined": defined_count,
        "required_artifacts_total": len(artifacts),
    }


def _extract_completion_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "objective_id": None,
            "completion_status": None,
            "done_status": None,
            "safe_closure_status": None,
            "completion_evidence_status": None,
            "closure_decision": None,
            "closure_reason": None,
            "completion_manual_required": None,
            "completion_replan_required": None,
            "lifecycle_alignment_status": None,
            "lifecycle_closure_status": None,
            "completion_blocked_reason": None,
            "required_evidence_total": 0,
            "missing_evidence_total": 0,
        }

    required_evidence = payload.get("required_evidence")
    missing_evidence = payload.get("missing_evidence")
    required = required_evidence if isinstance(required_evidence, list) else []
    missing = missing_evidence if isinstance(missing_evidence, list) else []

    return {
        "schema_version": payload.get("schema_version"),
        "objective_id": payload.get("objective_id"),
        "completion_status": payload.get("completion_status"),
        "done_status": payload.get("done_status"),
        "safe_closure_status": payload.get("safe_closure_status"),
        "completion_evidence_status": payload.get("completion_evidence_status"),
        "closure_decision": payload.get("closure_decision"),
        "closure_reason": payload.get("closure_reason"),
        "completion_manual_required": payload.get("completion_manual_required"),
        "completion_replan_required": payload.get("completion_replan_required"),
        "lifecycle_alignment_status": payload.get("lifecycle_alignment_status"),
        "lifecycle_closure_status": payload.get("lifecycle_closure_status"),
        "completion_blocked_reason": payload.get("completion_blocked_reason"),
        "required_evidence_total": len(required),
        "missing_evidence_total": len(missing),
    }


def _extract_approval_transport_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "completion_status": None,
            "approval_status": None,
            "approval_decision": None,
            "approval_scope": None,
            "approved_action": None,
            "approval_required": None,
            "approval_present": None,
            "approval_transport_status": None,
            "approval_compatibility_status": None,
            "approval_blocked_reason": None,
            "approval_superseded": None,
            "approval_stale": None,
            "approval_actor": None,
            "approval_recorded_at": None,
            "approval_expires_at": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "completion_status": payload.get("completion_status"),
        "approval_status": payload.get("approval_status"),
        "approval_decision": payload.get("approval_decision"),
        "approval_scope": payload.get("approval_scope"),
        "approved_action": payload.get("approved_action"),
        "approval_required": payload.get("approval_required"),
        "approval_present": payload.get("approval_present"),
        "approval_transport_status": payload.get("approval_transport_status"),
        "approval_compatibility_status": payload.get("approval_compatibility_status"),
        "approval_blocked_reason": payload.get("approval_blocked_reason"),
        "approval_superseded": payload.get("approval_superseded"),
        "approval_stale": payload.get("approval_stale"),
        "approval_actor": payload.get("approval_actor"),
        "approval_recorded_at": payload.get("approval_recorded_at"),
        "approval_expires_at": payload.get("approval_expires_at"),
    }


def _extract_reconcile_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "reconcile_status": None,
            "reconcile_decision": None,
            "reconcile_alignment_status": None,
            "reconcile_primary_mismatch": None,
            "reconcile_blocked_reason": None,
            "reconcile_waiting_on_truth": None,
            "reconcile_manual_required": None,
            "reconcile_replan_required": None,
            "reconcile_completion_status": None,
            "reconcile_approval_status": None,
            "reconcile_lifecycle_status": None,
            "reconcile_objective_status": None,
            "reconcile_transport_status": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "reconcile_status": payload.get("reconcile_status"),
        "reconcile_decision": payload.get("reconcile_decision"),
        "reconcile_alignment_status": payload.get("reconcile_alignment_status"),
        "reconcile_primary_mismatch": payload.get("reconcile_primary_mismatch"),
        "reconcile_blocked_reason": payload.get("reconcile_blocked_reason"),
        "reconcile_waiting_on_truth": payload.get("reconcile_waiting_on_truth"),
        "reconcile_manual_required": payload.get("reconcile_manual_required"),
        "reconcile_replan_required": payload.get("reconcile_replan_required"),
        "reconcile_completion_status": payload.get("reconcile_completion_status"),
        "reconcile_approval_status": payload.get("reconcile_approval_status"),
        "reconcile_lifecycle_status": payload.get("reconcile_lifecycle_status"),
        "reconcile_objective_status": payload.get("reconcile_objective_status"),
        "reconcile_transport_status": payload.get("reconcile_transport_status"),
    }


def _extract_repair_suggestion_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "repair_suggestion_status": None,
            "repair_suggestion_decision": None,
            "repair_suggestion_class": None,
            "repair_suggestion_priority": None,
            "repair_suggestion_confidence": None,
            "repair_primary_reason": None,
            "repair_manual_required": None,
            "repair_replan_required": None,
            "repair_truth_gathering_required": None,
            "repair_closure_followup_required": None,
            "repair_target_surface": None,
            "repair_precondition_status": None,
            "repair_reconcile_status": None,
            "repair_completion_status": None,
            "repair_approval_status": None,
            "repair_lifecycle_status": None,
            "repair_execution_recommended": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "repair_suggestion_status": payload.get("repair_suggestion_status"),
        "repair_suggestion_decision": payload.get("repair_suggestion_decision"),
        "repair_suggestion_class": payload.get("repair_suggestion_class"),
        "repair_suggestion_priority": payload.get("repair_suggestion_priority"),
        "repair_suggestion_confidence": payload.get("repair_suggestion_confidence"),
        "repair_primary_reason": payload.get("repair_primary_reason"),
        "repair_manual_required": payload.get("repair_manual_required"),
        "repair_replan_required": payload.get("repair_replan_required"),
        "repair_truth_gathering_required": payload.get("repair_truth_gathering_required"),
        "repair_closure_followup_required": payload.get("repair_closure_followup_required"),
        "repair_target_surface": payload.get("repair_target_surface"),
        "repair_precondition_status": payload.get("repair_precondition_status"),
        "repair_reconcile_status": payload.get("repair_reconcile_status"),
        "repair_completion_status": payload.get("repair_completion_status"),
        "repair_approval_status": payload.get("repair_approval_status"),
        "repair_lifecycle_status": payload.get("repair_lifecycle_status"),
        "repair_execution_recommended": payload.get("repair_execution_recommended"),
    }


def _extract_repair_plan_transport_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "repair_plan_status": None,
            "repair_plan_decision": None,
            "repair_plan_class": None,
            "repair_plan_priority": None,
            "repair_plan_confidence": None,
            "repair_plan_target_surface": None,
            "repair_plan_candidate_action": None,
            "repair_plan_precondition_status": None,
            "repair_plan_blocked_reason": None,
            "repair_plan_manual_required": None,
            "repair_plan_replan_required": None,
            "repair_plan_truth_gathering_required": None,
            "repair_plan_closure_followup_required": None,
            "repair_plan_execution_ready": None,
            "repair_plan_source_status": None,
            "repair_plan_reconcile_status": None,
            "repair_plan_suggestion_status": None,
            "repair_plan_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "repair_plan_status": payload.get("repair_plan_status"),
        "repair_plan_decision": payload.get("repair_plan_decision"),
        "repair_plan_class": payload.get("repair_plan_class"),
        "repair_plan_priority": payload.get("repair_plan_priority"),
        "repair_plan_confidence": payload.get("repair_plan_confidence"),
        "repair_plan_target_surface": payload.get("repair_plan_target_surface"),
        "repair_plan_candidate_action": payload.get("repair_plan_candidate_action"),
        "repair_plan_precondition_status": payload.get("repair_plan_precondition_status"),
        "repair_plan_blocked_reason": payload.get("repair_plan_blocked_reason"),
        "repair_plan_manual_required": payload.get("repair_plan_manual_required"),
        "repair_plan_replan_required": payload.get("repair_plan_replan_required"),
        "repair_plan_truth_gathering_required": payload.get("repair_plan_truth_gathering_required"),
        "repair_plan_closure_followup_required": payload.get("repair_plan_closure_followup_required"),
        "repair_plan_execution_ready": payload.get("repair_plan_execution_ready"),
        "repair_plan_source_status": payload.get("repair_plan_source_status"),
        "repair_plan_reconcile_status": payload.get("repair_plan_reconcile_status"),
        "repair_plan_suggestion_status": payload.get("repair_plan_suggestion_status"),
        "repair_plan_primary_reason": payload.get("repair_plan_primary_reason"),
    }


def _extract_repair_approval_binding_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "repair_plan_status": None,
            "approval_status": None,
            "repair_approval_binding_status": None,
            "repair_approval_binding_decision": None,
            "repair_approval_binding_scope": None,
            "repair_approval_binding_validity": None,
            "repair_approval_binding_compatibility_status": None,
            "repair_approval_binding_primary_reason": None,
            "repair_approval_binding_blocked_reason": None,
            "repair_approval_binding_manual_required": None,
            "repair_approval_binding_replan_required": None,
            "repair_approval_binding_truth_gathering_required": None,
            "repair_approval_binding_execution_authorized": None,
            "repair_approval_binding_source_status": None,
            "repair_approval_binding_plan_status": None,
            "repair_approval_binding_plan_action": None,
            "repair_approval_binding_approval_decision": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "repair_plan_status": payload.get("repair_plan_status"),
        "approval_status": payload.get("approval_status"),
        "repair_approval_binding_status": payload.get("repair_approval_binding_status"),
        "repair_approval_binding_decision": payload.get("repair_approval_binding_decision"),
        "repair_approval_binding_scope": payload.get("repair_approval_binding_scope"),
        "repair_approval_binding_validity": payload.get("repair_approval_binding_validity"),
        "repair_approval_binding_compatibility_status": payload.get(
            "repair_approval_binding_compatibility_status"
        ),
        "repair_approval_binding_primary_reason": payload.get("repair_approval_binding_primary_reason"),
        "repair_approval_binding_blocked_reason": payload.get("repair_approval_binding_blocked_reason"),
        "repair_approval_binding_manual_required": payload.get("repair_approval_binding_manual_required"),
        "repair_approval_binding_replan_required": payload.get("repair_approval_binding_replan_required"),
        "repair_approval_binding_truth_gathering_required": payload.get(
            "repair_approval_binding_truth_gathering_required"
        ),
        "repair_approval_binding_execution_authorized": payload.get(
            "repair_approval_binding_execution_authorized"
        ),
        "repair_approval_binding_source_status": payload.get("repair_approval_binding_source_status"),
        "repair_approval_binding_plan_status": payload.get("repair_approval_binding_plan_status"),
        "repair_approval_binding_plan_action": payload.get("repair_approval_binding_plan_action"),
        "repair_approval_binding_approval_decision": payload.get(
            "repair_approval_binding_approval_decision"
        ),
    }


def _extract_execution_authorization_gate_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "execution_authorization_status": None,
            "execution_authorization_decision": None,
            "execution_authorization_scope": None,
            "execution_authorization_validity": None,
            "execution_authorization_confidence": None,
            "execution_authorization_primary_reason": None,
            "execution_authorization_blocked_reason": None,
            "execution_authorization_manual_required": None,
            "execution_authorization_replan_required": None,
            "execution_authorization_truth_gathering_required": None,
            "execution_authorization_denied": None,
            "execution_authorization_eligible": None,
            "execution_authorization_source_status": None,
            "execution_authorization_binding_status": None,
            "execution_authorization_plan_status": None,
            "execution_authorization_approval_status": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "execution_authorization_status": payload.get("execution_authorization_status"),
        "execution_authorization_decision": payload.get("execution_authorization_decision"),
        "execution_authorization_scope": payload.get("execution_authorization_scope"),
        "execution_authorization_validity": payload.get("execution_authorization_validity"),
        "execution_authorization_confidence": payload.get("execution_authorization_confidence"),
        "execution_authorization_primary_reason": payload.get("execution_authorization_primary_reason"),
        "execution_authorization_blocked_reason": payload.get("execution_authorization_blocked_reason"),
        "execution_authorization_manual_required": payload.get("execution_authorization_manual_required"),
        "execution_authorization_replan_required": payload.get("execution_authorization_replan_required"),
        "execution_authorization_truth_gathering_required": payload.get(
            "execution_authorization_truth_gathering_required"
        ),
        "execution_authorization_denied": payload.get("execution_authorization_denied"),
        "execution_authorization_eligible": payload.get("execution_authorization_eligible"),
        "execution_authorization_source_status": payload.get("execution_authorization_source_status"),
        "execution_authorization_binding_status": payload.get("execution_authorization_binding_status"),
        "execution_authorization_plan_status": payload.get("execution_authorization_plan_status"),
        "execution_authorization_approval_status": payload.get("execution_authorization_approval_status"),
    }


def _extract_bounded_execution_bridge_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "bounded_execution_status": None,
            "bounded_execution_decision": None,
            "bounded_execution_scope": None,
            "bounded_execution_candidate_action": None,
            "bounded_execution_validity": None,
            "bounded_execution_confidence": None,
            "bounded_execution_primary_reason": None,
            "bounded_execution_blocked_reason": None,
            "bounded_execution_manual_required": None,
            "bounded_execution_replan_required": None,
            "bounded_execution_truth_gathering_required": None,
            "bounded_execution_ready": None,
            "bounded_execution_deferred": None,
            "bounded_execution_denied": None,
            "bounded_execution_source_status": None,
            "bounded_execution_authorization_status": None,
            "bounded_execution_binding_status": None,
            "bounded_execution_plan_status": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "bounded_execution_status": payload.get("bounded_execution_status"),
        "bounded_execution_decision": payload.get("bounded_execution_decision"),
        "bounded_execution_scope": payload.get("bounded_execution_scope"),
        "bounded_execution_candidate_action": payload.get("bounded_execution_candidate_action"),
        "bounded_execution_validity": payload.get("bounded_execution_validity"),
        "bounded_execution_confidence": payload.get("bounded_execution_confidence"),
        "bounded_execution_primary_reason": payload.get("bounded_execution_primary_reason"),
        "bounded_execution_blocked_reason": payload.get("bounded_execution_blocked_reason"),
        "bounded_execution_manual_required": payload.get("bounded_execution_manual_required"),
        "bounded_execution_replan_required": payload.get("bounded_execution_replan_required"),
        "bounded_execution_truth_gathering_required": payload.get(
            "bounded_execution_truth_gathering_required"
        ),
        "bounded_execution_ready": payload.get("bounded_execution_ready"),
        "bounded_execution_deferred": payload.get("bounded_execution_deferred"),
        "bounded_execution_denied": payload.get("bounded_execution_denied"),
        "bounded_execution_source_status": payload.get("bounded_execution_source_status"),
        "bounded_execution_authorization_status": payload.get(
            "bounded_execution_authorization_status"
        ),
        "bounded_execution_binding_status": payload.get("bounded_execution_binding_status"),
        "bounded_execution_plan_status": payload.get("bounded_execution_plan_status"),
    }


def _extract_execution_result_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "execution_result_status": None,
            "execution_result_outcome": None,
            "execution_result_validity": None,
            "execution_result_confidence": None,
            "execution_result_primary_reason": None,
            "execution_result_attempted": None,
            "execution_result_receipt_present": None,
            "execution_result_output_present": None,
            "execution_result_patch_present": None,
            "execution_result_patch_applied": None,
            "execution_result_test_result_present": None,
            "execution_result_test_passed": None,
            "execution_result_command_result_present": None,
            "execution_result_command_succeeded": None,
            "execution_result_blocked": None,
            "execution_result_not_executed": None,
            "execution_result_partial": None,
            "execution_result_failed": None,
            "execution_result_succeeded": None,
            "execution_result_unknown": None,
            "execution_result_manual_followup_required": None,
            "execution_result_source_posture": None,
            "execution_result_bridge_status": None,
            "execution_result_bridge_decision": None,
            "execution_result_authorization_status": None,
            "result_artifact_path": None,
            "execution_receipt_path": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "execution_result_status": payload.get("execution_result_status"),
        "execution_result_outcome": payload.get("execution_result_outcome"),
        "execution_result_validity": payload.get("execution_result_validity"),
        "execution_result_confidence": payload.get("execution_result_confidence"),
        "execution_result_primary_reason": payload.get("execution_result_primary_reason"),
        "execution_result_attempted": payload.get("execution_result_attempted"),
        "execution_result_receipt_present": payload.get("execution_result_receipt_present"),
        "execution_result_output_present": payload.get("execution_result_output_present"),
        "execution_result_patch_present": payload.get("execution_result_patch_present"),
        "execution_result_patch_applied": payload.get("execution_result_patch_applied"),
        "execution_result_test_result_present": payload.get("execution_result_test_result_present"),
        "execution_result_test_passed": payload.get("execution_result_test_passed"),
        "execution_result_command_result_present": payload.get("execution_result_command_result_present"),
        "execution_result_command_succeeded": payload.get("execution_result_command_succeeded"),
        "execution_result_blocked": payload.get("execution_result_blocked"),
        "execution_result_not_executed": payload.get("execution_result_not_executed"),
        "execution_result_partial": payload.get("execution_result_partial"),
        "execution_result_failed": payload.get("execution_result_failed"),
        "execution_result_succeeded": payload.get("execution_result_succeeded"),
        "execution_result_unknown": payload.get("execution_result_unknown"),
        "execution_result_manual_followup_required": payload.get(
            "execution_result_manual_followup_required"
        ),
        "execution_result_source_posture": payload.get("execution_result_source_posture"),
        "execution_result_bridge_status": payload.get("execution_result_bridge_status"),
        "execution_result_bridge_decision": payload.get("execution_result_bridge_decision"),
        "execution_result_authorization_status": payload.get("execution_result_authorization_status"),
        "result_artifact_path": payload.get("result_artifact_path"),
        "execution_receipt_path": payload.get("execution_receipt_path"),
    }


def _extract_verification_closure_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "verification_status": None,
            "verification_outcome": None,
            "verification_validity": None,
            "verification_confidence": None,
            "verification_primary_reason": None,
            "objective_satisfaction_status": None,
            "completion_satisfaction_status": None,
            "closure_status": None,
            "closure_decision": None,
            "objective_satisfied": None,
            "completion_satisfied": None,
            "safely_closable": None,
            "manual_closure_required": None,
            "closure_followup_required": None,
            "rollback_consideration_required": None,
            "external_truth_required": None,
            "verification_source_posture": None,
            "verification_bridge_status": None,
            "verification_bridge_decision": None,
            "verification_execution_result_status": None,
            "verification_execution_result_outcome": None,
            "verification_authorization_status": None,
            "result_artifact_path": None,
            "execution_receipt_path": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "verification_status": payload.get("verification_status"),
        "verification_outcome": payload.get("verification_outcome"),
        "verification_validity": payload.get("verification_validity"),
        "verification_confidence": payload.get("verification_confidence"),
        "verification_primary_reason": payload.get("verification_primary_reason"),
        "objective_satisfaction_status": payload.get("objective_satisfaction_status"),
        "completion_satisfaction_status": payload.get("completion_satisfaction_status"),
        "closure_status": payload.get("closure_status"),
        "closure_decision": payload.get("closure_decision"),
        "objective_satisfied": payload.get("objective_satisfied"),
        "completion_satisfied": payload.get("completion_satisfied"),
        "safely_closable": payload.get("safely_closable"),
        "manual_closure_required": payload.get("manual_closure_required"),
        "closure_followup_required": payload.get("closure_followup_required"),
        "rollback_consideration_required": payload.get("rollback_consideration_required"),
        "external_truth_required": payload.get("external_truth_required"),
        "verification_source_posture": payload.get("verification_source_posture"),
        "verification_bridge_status": payload.get("verification_bridge_status"),
        "verification_bridge_decision": payload.get("verification_bridge_decision"),
        "verification_execution_result_status": payload.get(
            "verification_execution_result_status"
        ),
        "verification_execution_result_outcome": payload.get(
            "verification_execution_result_outcome"
        ),
        "verification_authorization_status": payload.get(
            "verification_authorization_status"
        ),
        "result_artifact_path": payload.get("result_artifact_path"),
        "execution_receipt_path": payload.get("execution_receipt_path"),
    }


def _extract_retry_reentry_loop_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "retry_loop_status": None,
            "retry_loop_decision": None,
            "retry_loop_validity": None,
            "retry_loop_confidence": None,
            "loop_primary_reason": None,
            "attempt_count": None,
            "max_attempt_count": None,
            "reentry_count": None,
            "max_reentry_count": None,
            "same_failure_count": None,
            "max_same_failure_count": None,
            "retry_allowed": None,
            "reentry_allowed": None,
            "retry_exhausted": None,
            "reentry_exhausted": None,
            "same_failure_exhausted": None,
            "terminal_stop_required": None,
            "manual_escalation_required": None,
            "replan_required": None,
            "recollect_required": None,
            "same_lane_retry_allowed": None,
            "repair_retry_allowed": None,
            "no_progress_stop_required": None,
            "loop_stop_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "retry_loop_status": payload.get("retry_loop_status"),
        "retry_loop_decision": payload.get("retry_loop_decision"),
        "retry_loop_validity": payload.get("retry_loop_validity"),
        "retry_loop_confidence": payload.get("retry_loop_confidence"),
        "loop_primary_reason": payload.get("loop_primary_reason"),
        "attempt_count": payload.get("attempt_count"),
        "max_attempt_count": payload.get("max_attempt_count"),
        "reentry_count": payload.get("reentry_count"),
        "max_reentry_count": payload.get("max_reentry_count"),
        "same_failure_count": payload.get("same_failure_count"),
        "max_same_failure_count": payload.get("max_same_failure_count"),
        "retry_allowed": payload.get("retry_allowed"),
        "reentry_allowed": payload.get("reentry_allowed"),
        "retry_exhausted": payload.get("retry_exhausted"),
        "reentry_exhausted": payload.get("reentry_exhausted"),
        "same_failure_exhausted": payload.get("same_failure_exhausted"),
        "terminal_stop_required": payload.get("terminal_stop_required"),
        "manual_escalation_required": payload.get("manual_escalation_required"),
        "replan_required": payload.get("replan_required"),
        "recollect_required": payload.get("recollect_required"),
        "same_lane_retry_allowed": payload.get("same_lane_retry_allowed"),
        "repair_retry_allowed": payload.get("repair_retry_allowed"),
        "no_progress_stop_required": payload.get("no_progress_stop_required"),
        "loop_stop_reason": payload.get("loop_stop_reason"),
    }


def _extract_endgame_closure_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "endgame_closure_status": None,
            "endgame_closure_outcome": None,
            "endgame_closure_validity": None,
            "endgame_closure_confidence": None,
            "final_closure_class": None,
            "terminal_stop_class": None,
            "closure_resolution_status": None,
            "endgame_primary_reason": None,
            "safely_closed": None,
            "completed_but_not_closed": None,
            "rollback_complete_but_not_closed": None,
            "manual_closure_only": None,
            "external_truth_pending": None,
            "closure_unresolved": None,
            "terminal_success": None,
            "terminal_non_success": None,
            "operator_followup_required": None,
            "further_retry_allowed": None,
            "further_reentry_allowed": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "endgame_closure_status": payload.get("endgame_closure_status"),
        "endgame_closure_outcome": payload.get("endgame_closure_outcome"),
        "endgame_closure_validity": payload.get("endgame_closure_validity"),
        "endgame_closure_confidence": payload.get("endgame_closure_confidence"),
        "final_closure_class": payload.get("final_closure_class"),
        "terminal_stop_class": payload.get("terminal_stop_class"),
        "closure_resolution_status": payload.get("closure_resolution_status"),
        "endgame_primary_reason": payload.get("endgame_primary_reason"),
        "safely_closed": payload.get("safely_closed"),
        "completed_but_not_closed": payload.get("completed_but_not_closed"),
        "rollback_complete_but_not_closed": payload.get("rollback_complete_but_not_closed"),
        "manual_closure_only": payload.get("manual_closure_only"),
        "external_truth_pending": payload.get("external_truth_pending"),
        "closure_unresolved": payload.get("closure_unresolved"),
        "terminal_success": payload.get("terminal_success"),
        "terminal_non_success": payload.get("terminal_non_success"),
        "operator_followup_required": payload.get("operator_followup_required"),
        "further_retry_allowed": payload.get("further_retry_allowed"),
        "further_reentry_allowed": payload.get("further_reentry_allowed"),
    }


def _extract_loop_hardening_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "loop_hardening_status": None,
            "loop_hardening_decision": None,
            "loop_hardening_validity": None,
            "loop_hardening_confidence": None,
            "loop_hardening_primary_reason": None,
            "same_failure_signature": None,
            "same_failure_bucket": None,
            "same_failure_persistence": None,
            "no_progress_status": None,
            "oscillation_status": None,
            "retry_freeze_status": None,
            "same_failure_detected": None,
            "same_failure_stop_required": None,
            "no_progress_detected": None,
            "no_progress_stop_required": None,
            "oscillation_detected": None,
            "unstable_loop_detected": None,
            "retry_freeze_required": None,
            "cool_down_required": None,
            "forced_manual_escalation_required": None,
            "hardening_stop_required": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "loop_hardening_status": payload.get("loop_hardening_status"),
        "loop_hardening_decision": payload.get("loop_hardening_decision"),
        "loop_hardening_validity": payload.get("loop_hardening_validity"),
        "loop_hardening_confidence": payload.get("loop_hardening_confidence"),
        "loop_hardening_primary_reason": payload.get("loop_hardening_primary_reason"),
        "same_failure_signature": payload.get("same_failure_signature"),
        "same_failure_bucket": payload.get("same_failure_bucket"),
        "same_failure_persistence": payload.get("same_failure_persistence"),
        "no_progress_status": payload.get("no_progress_status"),
        "oscillation_status": payload.get("oscillation_status"),
        "retry_freeze_status": payload.get("retry_freeze_status"),
        "same_failure_detected": payload.get("same_failure_detected"),
        "same_failure_stop_required": payload.get("same_failure_stop_required"),
        "no_progress_detected": payload.get("no_progress_detected"),
        "no_progress_stop_required": payload.get("no_progress_stop_required"),
        "oscillation_detected": payload.get("oscillation_detected"),
        "unstable_loop_detected": payload.get("unstable_loop_detected"),
        "retry_freeze_required": payload.get("retry_freeze_required"),
        "cool_down_required": payload.get("cool_down_required"),
        "forced_manual_escalation_required": payload.get(
            "forced_manual_escalation_required"
        ),
        "hardening_stop_required": payload.get("hardening_stop_required"),
    }


def _extract_lane_stabilization_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "lane_status": None,
            "lane_decision": None,
            "lane_validity": None,
            "lane_confidence": None,
            "current_lane": None,
            "target_lane": None,
            "lane_transition_status": None,
            "lane_transition_decision": None,
            "lane_preconditions_status": None,
            "lane_retry_policy_class": None,
            "lane_verification_policy_class": None,
            "lane_escalation_policy_class": None,
            "lane_primary_reason": None,
            "lane_execution_allowed": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "lane_status": payload.get("lane_status"),
        "lane_decision": payload.get("lane_decision"),
        "lane_validity": payload.get("lane_validity"),
        "lane_confidence": payload.get("lane_confidence"),
        "current_lane": payload.get("current_lane"),
        "target_lane": payload.get("target_lane"),
        "lane_transition_status": payload.get("lane_transition_status"),
        "lane_transition_decision": payload.get("lane_transition_decision"),
        "lane_preconditions_status": payload.get("lane_preconditions_status"),
        "lane_retry_policy_class": payload.get("lane_retry_policy_class"),
        "lane_verification_policy_class": payload.get("lane_verification_policy_class"),
        "lane_escalation_policy_class": payload.get("lane_escalation_policy_class"),
        "lane_primary_reason": payload.get("lane_primary_reason"),
        "lane_execution_allowed": payload.get("lane_execution_allowed"),
    }


def _extract_observability_rollup_contract_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "observability_status": None,
            "observability_validity": None,
            "observability_confidence": None,
            "run_terminal_class": None,
            "lane": None,
            "observability_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "observability_status": payload.get("observability_status"),
        "observability_validity": payload.get("observability_validity"),
        "observability_confidence": payload.get("observability_confidence"),
        "run_terminal_class": payload.get("run_terminal_class"),
        "lane": payload.get("lane"),
        "observability_primary_reason": payload.get("observability_primary_reason"),
    }


def _extract_failure_bucket_rollup_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "failure_bucket_status": None,
            "failure_bucket_validity": None,
            "failure_bucket_confidence": None,
            "primary_failure_bucket": None,
            "bucket_count": None,
            "failure_bucket_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "failure_bucket_status": payload.get("failure_bucket_status"),
        "failure_bucket_validity": payload.get("failure_bucket_validity"),
        "failure_bucket_confidence": payload.get("failure_bucket_confidence"),
        "primary_failure_bucket": payload.get("primary_failure_bucket"),
        "bucket_count": payload.get("bucket_count"),
        "failure_bucket_primary_reason": payload.get("failure_bucket_primary_reason"),
    }


def _extract_fleet_run_rollup_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "fleet_lane": None,
            "fleet_terminal_class": None,
            "fleet_primary_failure_bucket": None,
            "fleet_observability_status": None,
            "fleet_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "fleet_lane": payload.get("fleet_lane"),
        "fleet_terminal_class": payload.get("fleet_terminal_class"),
        "fleet_primary_failure_bucket": payload.get("fleet_primary_failure_bucket"),
        "fleet_observability_status": payload.get("fleet_observability_status"),
        "fleet_primary_reason": payload.get("fleet_primary_reason"),
    }


def _extract_failure_bucketing_hardening_contract_summary(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "failure_bucketing_status": None,
            "failure_bucketing_validity": None,
            "failure_bucketing_confidence": None,
            "primary_failure_bucket": None,
            "bucket_family": None,
            "bucket_severity": None,
            "bucket_stability_class": None,
            "bucket_terminality_class": None,
            "failure_bucketing_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "failure_bucketing_status": payload.get("failure_bucketing_status"),
        "failure_bucketing_validity": payload.get("failure_bucketing_validity"),
        "failure_bucketing_confidence": payload.get("failure_bucketing_confidence"),
        "primary_failure_bucket": payload.get("primary_failure_bucket"),
        "bucket_family": payload.get("bucket_family"),
        "bucket_severity": payload.get("bucket_severity"),
        "bucket_stability_class": payload.get("bucket_stability_class"),
        "bucket_terminality_class": payload.get("bucket_terminality_class"),
        "failure_bucketing_primary_reason": payload.get(
            "failure_bucketing_primary_reason"
        ),
    }


def _extract_retention_manifest_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "reference_layout_version": None,
            "reference_order_stable": None,
            "alias_deduplicated": None,
            "manifest_compact": None,
            "retention_manifest_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "reference_layout_version": payload.get("reference_layout_version"),
        "reference_order_stable": payload.get("reference_order_stable"),
        "alias_deduplicated": payload.get("alias_deduplicated"),
        "manifest_compact": payload.get("manifest_compact"),
        "retention_manifest_primary_reason": payload.get(
            "retention_manifest_primary_reason"
        ),
    }


def _extract_artifact_retention_contract_summary(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "artifact_retention_status": None,
            "artifact_retention_validity": None,
            "artifact_retention_confidence": None,
            "retention_policy_class": None,
            "retention_compaction_class": None,
            "retention_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "artifact_retention_status": payload.get("artifact_retention_status"),
        "artifact_retention_validity": payload.get("artifact_retention_validity"),
        "artifact_retention_confidence": payload.get("artifact_retention_confidence"),
        "retention_policy_class": payload.get("retention_policy_class"),
        "retention_compaction_class": payload.get("retention_compaction_class"),
        "retention_primary_reason": payload.get("retention_primary_reason"),
    }


def _extract_fleet_safety_control_contract_summary(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "schema_version": None,
            "run_id": None,
            "objective_id": None,
            "fleet_safety_status": None,
            "fleet_safety_validity": None,
            "fleet_safety_confidence": None,
            "fleet_safety_decision": None,
            "fleet_restart_decision": None,
            "fleet_safety_scope": None,
            "fleet_safety_primary_reason": None,
        }
    return {
        "schema_version": payload.get("schema_version"),
        "run_id": payload.get("run_id"),
        "objective_id": payload.get("objective_id"),
        "fleet_safety_status": payload.get("fleet_safety_status"),
        "fleet_safety_validity": payload.get("fleet_safety_validity"),
        "fleet_safety_confidence": payload.get("fleet_safety_confidence"),
        "fleet_safety_decision": payload.get("fleet_safety_decision"),
        "fleet_restart_decision": payload.get("fleet_restart_decision"),
        "fleet_safety_scope": payload.get("fleet_safety_scope"),
        "fleet_safety_primary_reason": payload.get("fleet_safety_primary_reason"),
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
                "objective_contract": None,
                "completion_contract": None,
                "approval_transport": None,
                "reconcile_contract": None,
                "repair_suggestion_contract": None,
                "repair_plan_transport": None,
                "repair_approval_binding": None,
                "execution_authorization_gate": None,
                "bounded_execution_bridge": None,
                "execution_result_contract": None,
                "verification_closure_contract": None,
                "retry_reentry_loop_contract": None,
                "endgame_closure_contract": None,
                "loop_hardening_contract": None,
                "lane_stabilization_contract": None,
                "observability_rollup_contract": None,
                "failure_bucket_rollup": None,
                "fleet_run_rollup": None,
                "failure_bucketing_hardening_contract": None,
                "retention_manifest": None,
                "artifact_retention_contract": None,
                "fleet_safety_control_contract": None,
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
            "objective_contract": _extract_objective_contract_summary(None),
            "completion_contract": _extract_completion_contract_summary(None),
            "approval_transport": _extract_approval_transport_summary(None),
            "reconcile_contract": _extract_reconcile_contract_summary(None),
            "repair_suggestion_contract": _extract_repair_suggestion_contract_summary(None),
            "repair_plan_transport": _extract_repair_plan_transport_summary(None),
            "repair_approval_binding": _extract_repair_approval_binding_summary(None),
            "execution_authorization_gate": _extract_execution_authorization_gate_summary(None),
            "bounded_execution_bridge": _extract_bounded_execution_bridge_summary(None),
            "execution_result_contract": _extract_execution_result_contract_summary(None),
            "verification_closure_contract": _extract_verification_closure_contract_summary(None),
            "retry_reentry_loop_contract": _extract_retry_reentry_loop_contract_summary(None),
            "endgame_closure_contract": _extract_endgame_closure_contract_summary(None),
            "loop_hardening_contract": _extract_loop_hardening_contract_summary(None),
            "lane_stabilization_contract": _extract_lane_stabilization_contract_summary(None),
            "observability_rollup_contract": _extract_observability_rollup_contract_summary(None),
            "failure_bucket_rollup": _extract_failure_bucket_rollup_summary(None),
            "fleet_run_rollup": _extract_fleet_run_rollup_summary(None),
            "failure_bucketing_hardening_contract": (
                _extract_failure_bucketing_hardening_contract_summary(None)
            ),
            "retention_manifest": _extract_retention_manifest_summary(None),
            "artifact_retention_contract": _extract_artifact_retention_contract_summary(
                None
            ),
            "fleet_safety_control_contract": _extract_fleet_safety_control_contract_summary(
                None
            ),
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
                "objective_contract_present": None,
                "objective_id": None,
                "objective_summary": None,
                "objective_type": None,
                "requested_outcome": None,
                "objective_acceptance_status": None,
                "objective_required_artifacts_status": None,
                "objective_scope_status": None,
                "objective_contract_status": None,
                "objective_contract_blocked_reason": None,
                "completion_contract_present": None,
                "completion_status": None,
                "done_status": None,
                "safe_closure_status": None,
                "completion_evidence_status": None,
                "completion_blocked_reason": None,
                "completion_manual_required": None,
                "completion_replan_required": None,
                "completion_lifecycle_alignment_status": None,
                "approval_transport_present": None,
                "approval_status": None,
                "approval_decision": None,
                "approval_scope": None,
                "approved_action": None,
                "approval_required": None,
                "approval_transport_status": None,
                "approval_compatibility_status": None,
                "approval_blocked_reason": None,
                "reconcile_contract_present": None,
                "reconcile_status": None,
                "reconcile_decision": None,
                "reconcile_alignment_status": None,
                "reconcile_primary_mismatch": None,
                "reconcile_blocked_reason": None,
                "reconcile_waiting_on_truth": None,
                "reconcile_manual_required": None,
                "reconcile_replan_required": None,
                "repair_suggestion_contract_present": None,
                "repair_suggestion_status": None,
                "repair_suggestion_decision": None,
                "repair_suggestion_class": None,
                "repair_suggestion_priority": None,
                "repair_suggestion_confidence": None,
                "repair_primary_reason": None,
                "repair_manual_required": None,
                "repair_replan_required": None,
                "repair_truth_gathering_required": None,
                "repair_plan_transport_present": None,
                "repair_plan_status": None,
                "repair_plan_decision": None,
                "repair_plan_class": None,
                "repair_plan_priority": None,
                "repair_plan_confidence": None,
                "repair_plan_target_surface": None,
                "repair_plan_candidate_action": None,
                "repair_plan_primary_reason": None,
                "repair_plan_manual_required": None,
                "repair_plan_replan_required": None,
                "repair_plan_truth_gathering_required": None,
                "repair_approval_binding_present": None,
                "repair_approval_binding_status": None,
                "repair_approval_binding_decision": None,
                "repair_approval_binding_scope": None,
                "repair_approval_binding_validity": None,
                "repair_approval_binding_compatibility_status": None,
                "repair_approval_binding_primary_reason": None,
                "repair_approval_binding_manual_required": None,
                "repair_approval_binding_replan_required": None,
                "repair_approval_binding_truth_gathering_required": None,
                "execution_authorization_gate_present": None,
                "execution_authorization_status": None,
                "execution_authorization_decision": None,
                "execution_authorization_scope": None,
                "execution_authorization_validity": None,
                "execution_authorization_confidence": None,
                "execution_authorization_primary_reason": None,
                "execution_authorization_manual_required": None,
                "execution_authorization_replan_required": None,
                "execution_authorization_truth_gathering_required": None,
                "bounded_execution_bridge_present": None,
                "bounded_execution_status": None,
                "bounded_execution_decision": None,
                "bounded_execution_scope": None,
                "bounded_execution_validity": None,
                "bounded_execution_confidence": None,
                "bounded_execution_primary_reason": None,
                "bounded_execution_manual_required": None,
                "bounded_execution_replan_required": None,
                "bounded_execution_truth_gathering_required": None,
                "execution_result_contract_present": None,
                "execution_result_status": None,
                "execution_result_outcome": None,
                "execution_result_validity": None,
                "execution_result_confidence": None,
                "execution_result_primary_reason": None,
                "execution_result_attempted": None,
                "execution_result_receipt_present": None,
                "execution_result_output_present": None,
                "execution_result_manual_followup_required": None,
                "verification_closure_contract_present": None,
                "verification_status": None,
                "verification_outcome": None,
                "verification_validity": None,
                "verification_confidence": None,
                "verification_primary_reason": None,
                "objective_satisfaction_status": None,
                "completion_satisfaction_status": None,
                "closure_status": None,
                "closure_decision": None,
                "objective_satisfied": None,
                "completion_satisfied": None,
                "safely_closable": None,
                "manual_closure_required": None,
                "closure_followup_required": None,
                "external_truth_required": None,
                "retry_reentry_loop_contract_present": None,
                "retry_loop_status": None,
                "retry_loop_decision": None,
                "retry_loop_validity": None,
                "retry_loop_confidence": None,
                "loop_primary_reason": None,
                "attempt_count": None,
                "max_attempt_count": None,
                "reentry_count": None,
                "max_reentry_count": None,
                "same_failure_count": None,
                "max_same_failure_count": None,
                "retry_allowed": None,
                "reentry_allowed": None,
                "retry_exhausted": None,
                "reentry_exhausted": None,
                "same_failure_exhausted": None,
                "terminal_stop_required": None,
                "manual_escalation_required": None,
                "replan_required": None,
                "recollect_required": None,
                "same_lane_retry_allowed": None,
                "repair_retry_allowed": None,
                "no_progress_stop_required": None,
                "endgame_closure_contract_present": None,
                "endgame_closure_status": None,
                "endgame_closure_outcome": None,
                "endgame_closure_validity": None,
                "endgame_closure_confidence": None,
                "final_closure_class": None,
                "terminal_stop_class": None,
                "closure_resolution_status": None,
                "endgame_primary_reason": None,
                "safely_closed": None,
                "completed_but_not_closed": None,
                "rollback_complete_but_not_closed": None,
                "manual_closure_only": None,
                "external_truth_pending": None,
                "closure_unresolved": None,
                "terminal_success": None,
                "terminal_non_success": None,
                "operator_followup_required": None,
                "further_retry_allowed": None,
                "further_reentry_allowed": None,
                "loop_hardening_contract_present": None,
                "loop_hardening_status": None,
                "loop_hardening_decision": None,
                "loop_hardening_validity": None,
                "loop_hardening_confidence": None,
                "loop_hardening_primary_reason": None,
                "same_failure_signature": None,
                "same_failure_bucket": None,
                "same_failure_persistence": None,
                "no_progress_status": None,
                "oscillation_status": None,
                "retry_freeze_status": None,
                "same_failure_detected": None,
                "same_failure_stop_required": None,
                "no_progress_detected": None,
                "oscillation_detected": None,
                "unstable_loop_detected": None,
                "retry_freeze_required": None,
                "cool_down_required": None,
                "forced_manual_escalation_required": None,
                "hardening_stop_required": None,
                "lane_stabilization_contract_present": None,
                "lane_status": None,
                "lane_decision": None,
                "lane_validity": None,
                "lane_confidence": None,
                "current_lane": None,
                "target_lane": None,
                "lane_transition_status": None,
                "lane_transition_decision": None,
                "lane_preconditions_status": None,
                "lane_retry_policy_class": None,
                "lane_verification_policy_class": None,
                "lane_escalation_policy_class": None,
                "lane_attempt_budget": None,
                "lane_reentry_budget": None,
                "lane_transition_count": None,
                "max_lane_transition_count": None,
                "lane_primary_reason": None,
                "lane_valid": None,
                "lane_mismatch_detected": None,
                "lane_transition_required": None,
                "lane_transition_allowed": None,
                "lane_transition_blocked": None,
                "lane_stop_required": None,
                "lane_manual_review_required": None,
                "lane_replan_required": None,
                "lane_truth_gathering_required": None,
                "lane_execution_allowed": None,
                "observability_rollup_present": None,
                "failure_bucketing_hardening_present": None,
                "artifact_retention_present": None,
                "fleet_safety_control_present": None,
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
    objective_contract_path = run_root / "objective_contract.json"
    completion_contract_path = run_root / "completion_contract.json"
    approval_transport_path = run_root / "approval_transport.json"
    reconcile_contract_path = run_root / "reconcile_contract.json"
    repair_suggestion_contract_path = run_root / "repair_suggestion_contract.json"
    repair_plan_transport_path = run_root / "repair_plan_transport.json"
    repair_approval_binding_path = run_root / "repair_approval_binding.json"
    execution_authorization_gate_path = run_root / "execution_authorization_gate.json"
    bounded_execution_bridge_path = run_root / "bounded_execution_bridge.json"
    execution_result_contract_path = run_root / "execution_result_contract.json"
    verification_closure_contract_path = run_root / "verification_closure_contract.json"
    retry_reentry_loop_contract_path = run_root / "retry_reentry_loop_contract.json"
    endgame_closure_contract_path = run_root / "endgame_closure_contract.json"
    loop_hardening_contract_path = run_root / "loop_hardening_contract.json"
    lane_stabilization_contract_path = run_root / "lane_stabilization_contract.json"
    observability_rollup_contract_path = run_root / "observability_rollup_contract.json"
    failure_bucket_rollup_path = run_root / "failure_bucket_rollup.json"
    fleet_run_rollup_path = run_root / "fleet_run_rollup.json"
    failure_bucketing_hardening_contract_path = (
        run_root / "failure_bucketing_hardening_contract.json"
    )
    retention_manifest_path = run_root / "retention_manifest.json"
    artifact_retention_contract_path = run_root / "artifact_retention_contract.json"
    fleet_safety_control_contract_path = run_root / "fleet_safety_control_contract.json"

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
    objective_contract_payload = _read_json(str(objective_contract_path))
    completion_contract_payload = _read_json(str(completion_contract_path))
    approval_transport_payload = _read_json(str(approval_transport_path))
    reconcile_contract_payload = _read_json(str(reconcile_contract_path))
    repair_suggestion_contract_payload = _read_json(str(repair_suggestion_contract_path))
    repair_plan_transport_payload = _read_json(str(repair_plan_transport_path))
    repair_approval_binding_payload = _read_json(str(repair_approval_binding_path))
    execution_authorization_gate_payload = _read_json(str(execution_authorization_gate_path))
    bounded_execution_bridge_payload = _read_json(str(bounded_execution_bridge_path))
    execution_result_contract_payload = _read_json(str(execution_result_contract_path))
    verification_closure_contract_payload = _read_json(
        str(verification_closure_contract_path)
    )
    retry_reentry_loop_contract_payload = _read_json(
        str(retry_reentry_loop_contract_path)
    )
    endgame_closure_contract_payload = _read_json(
        str(endgame_closure_contract_path)
    )
    loop_hardening_contract_payload = _read_json(
        str(loop_hardening_contract_path)
    )
    lane_stabilization_contract_payload = _read_json(
        str(lane_stabilization_contract_path)
    )
    observability_rollup_contract_payload = _read_json(
        str(observability_rollup_contract_path)
    )
    failure_bucket_rollup_payload = _read_json(str(failure_bucket_rollup_path))
    fleet_run_rollup_payload = _read_json(str(fleet_run_rollup_path))
    failure_bucketing_hardening_contract_payload = _read_json(
        str(failure_bucketing_hardening_contract_path)
    )
    retention_manifest_payload = _read_json(str(retention_manifest_path))
    artifact_retention_contract_payload = _read_json(
        str(artifact_retention_contract_path)
    )
    fleet_safety_control_contract_payload = _read_json(
        str(fleet_safety_control_contract_path)
    )

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
            "objective_contract": str(objective_contract_path) if objective_contract_path.exists() else None,
            "completion_contract": str(completion_contract_path) if completion_contract_path.exists() else None,
            "approval_transport": str(approval_transport_path) if approval_transport_path.exists() else None,
            "reconcile_contract": str(reconcile_contract_path) if reconcile_contract_path.exists() else None,
            "repair_suggestion_contract": (
                str(repair_suggestion_contract_path) if repair_suggestion_contract_path.exists() else None
            ),
            "repair_plan_transport": (
                str(repair_plan_transport_path) if repair_plan_transport_path.exists() else None
            ),
            "repair_approval_binding": (
                str(repair_approval_binding_path) if repair_approval_binding_path.exists() else None
            ),
            "execution_authorization_gate": (
                str(execution_authorization_gate_path)
                if execution_authorization_gate_path.exists()
                else None
            ),
            "bounded_execution_bridge": (
                str(bounded_execution_bridge_path)
                if bounded_execution_bridge_path.exists()
                else None
            ),
            "execution_result_contract": (
                str(execution_result_contract_path)
                if execution_result_contract_path.exists()
                else None
            ),
            "verification_closure_contract": (
                str(verification_closure_contract_path)
                if verification_closure_contract_path.exists()
                else None
            ),
            "retry_reentry_loop_contract": (
                str(retry_reentry_loop_contract_path)
                if retry_reentry_loop_contract_path.exists()
                else None
            ),
            "endgame_closure_contract": (
                str(endgame_closure_contract_path)
                if endgame_closure_contract_path.exists()
                else None
            ),
            "loop_hardening_contract": (
                str(loop_hardening_contract_path)
                if loop_hardening_contract_path.exists()
                else None
            ),
            "lane_stabilization_contract": (
                str(lane_stabilization_contract_path)
                if lane_stabilization_contract_path.exists()
                else None
            ),
            "observability_rollup_contract": (
                str(observability_rollup_contract_path)
                if observability_rollup_contract_path.exists()
                else None
            ),
            "failure_bucket_rollup": (
                str(failure_bucket_rollup_path)
                if failure_bucket_rollup_path.exists()
                else None
            ),
            "fleet_run_rollup": (
                str(fleet_run_rollup_path)
                if fleet_run_rollup_path.exists()
                else None
            ),
            "failure_bucketing_hardening_contract": (
                str(failure_bucketing_hardening_contract_path)
                if failure_bucketing_hardening_contract_path.exists()
                else None
            ),
            "retention_manifest": (
                str(retention_manifest_path) if retention_manifest_path.exists() else None
            ),
            "artifact_retention_contract": (
                str(artifact_retention_contract_path)
                if artifact_retention_contract_path.exists()
                else None
            ),
            "fleet_safety_control_contract": (
                str(fleet_safety_control_contract_path)
                if fleet_safety_control_contract_path.exists()
                else None
            ),
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
        "objective_contract": _extract_objective_contract_summary(objective_contract_payload),
        "completion_contract": _extract_completion_contract_summary(completion_contract_payload),
        "approval_transport": _extract_approval_transport_summary(approval_transport_payload),
        "reconcile_contract": _extract_reconcile_contract_summary(reconcile_contract_payload),
        "repair_suggestion_contract": _extract_repair_suggestion_contract_summary(
            repair_suggestion_contract_payload
        ),
        "repair_plan_transport": _extract_repair_plan_transport_summary(
            repair_plan_transport_payload
        ),
        "repair_approval_binding": _extract_repair_approval_binding_summary(
            repair_approval_binding_payload
        ),
        "execution_authorization_gate": _extract_execution_authorization_gate_summary(
            execution_authorization_gate_payload
        ),
        "bounded_execution_bridge": _extract_bounded_execution_bridge_summary(
            bounded_execution_bridge_payload
        ),
        "execution_result_contract": _extract_execution_result_contract_summary(
            execution_result_contract_payload
        ),
        "verification_closure_contract": _extract_verification_closure_contract_summary(
            verification_closure_contract_payload
        ),
        "retry_reentry_loop_contract": _extract_retry_reentry_loop_contract_summary(
            retry_reentry_loop_contract_payload
        ),
        "endgame_closure_contract": _extract_endgame_closure_contract_summary(
            endgame_closure_contract_payload
        ),
        "loop_hardening_contract": _extract_loop_hardening_contract_summary(
            loop_hardening_contract_payload
        ),
        "lane_stabilization_contract": _extract_lane_stabilization_contract_summary(
            lane_stabilization_contract_payload
        ),
        "observability_rollup_contract": _extract_observability_rollup_contract_summary(
            observability_rollup_contract_payload
        ),
        "failure_bucket_rollup": _extract_failure_bucket_rollup_summary(
            failure_bucket_rollup_payload
        ),
        "fleet_run_rollup": _extract_fleet_run_rollup_summary(
            fleet_run_rollup_payload
        ),
        "failure_bucketing_hardening_contract": (
            _extract_failure_bucketing_hardening_contract_summary(
                failure_bucketing_hardening_contract_payload
            )
        ),
        "retention_manifest": _extract_retention_manifest_summary(
            retention_manifest_payload
        ),
        "artifact_retention_contract": _extract_artifact_retention_contract_summary(
            artifact_retention_contract_payload
        ),
        "fleet_safety_control_contract": _extract_fleet_safety_control_contract_summary(
            fleet_safety_control_contract_payload
        ),
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
            "objective_contract_present": (
                run_state_payload.get("objective_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_id": (
                run_state_payload.get("objective_id")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_summary": (
                run_state_payload.get("objective_summary")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_type": (
                run_state_payload.get("objective_type")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "requested_outcome": (
                run_state_payload.get("requested_outcome")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_acceptance_status": (
                run_state_payload.get("objective_acceptance_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_required_artifacts_status": (
                run_state_payload.get("objective_required_artifacts_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_scope_status": (
                run_state_payload.get("objective_scope_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_contract_status": (
                run_state_payload.get("objective_contract_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_contract_blocked_reason": (
                run_state_payload.get("objective_contract_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_contract_present": (
                run_state_payload.get("completion_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_status": (
                run_state_payload.get("completion_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "done_status": (
                run_state_payload.get("done_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "safe_closure_status": (
                run_state_payload.get("safe_closure_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_evidence_status": (
                run_state_payload.get("completion_evidence_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_blocked_reason": (
                run_state_payload.get("completion_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_manual_required": (
                run_state_payload.get("completion_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_replan_required": (
                run_state_payload.get("completion_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_lifecycle_alignment_status": (
                run_state_payload.get("completion_lifecycle_alignment_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_transport_present": (
                run_state_payload.get("approval_transport_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_status": (
                run_state_payload.get("approval_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_decision": (
                run_state_payload.get("approval_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_scope": (
                run_state_payload.get("approval_scope")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approved_action": (
                run_state_payload.get("approved_action")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_required": (
                run_state_payload.get("approval_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_transport_status": (
                run_state_payload.get("approval_transport_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_compatibility_status": (
                run_state_payload.get("approval_compatibility_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "approval_blocked_reason": (
                run_state_payload.get("approval_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_contract_present": (
                run_state_payload.get("reconcile_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_status": (
                run_state_payload.get("reconcile_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_decision": (
                run_state_payload.get("reconcile_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_alignment_status": (
                run_state_payload.get("reconcile_alignment_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_primary_mismatch": (
                run_state_payload.get("reconcile_primary_mismatch")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_blocked_reason": (
                run_state_payload.get("reconcile_blocked_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_waiting_on_truth": (
                run_state_payload.get("reconcile_waiting_on_truth")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_manual_required": (
                run_state_payload.get("reconcile_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reconcile_replan_required": (
                run_state_payload.get("reconcile_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_suggestion_contract_present": (
                run_state_payload.get("repair_suggestion_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_suggestion_status": (
                run_state_payload.get("repair_suggestion_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_suggestion_decision": (
                run_state_payload.get("repair_suggestion_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_suggestion_class": (
                run_state_payload.get("repair_suggestion_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_suggestion_priority": (
                run_state_payload.get("repair_suggestion_priority")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_suggestion_confidence": (
                run_state_payload.get("repair_suggestion_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_primary_reason": (
                run_state_payload.get("repair_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_manual_required": (
                run_state_payload.get("repair_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_replan_required": (
                run_state_payload.get("repair_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_truth_gathering_required": (
                run_state_payload.get("repair_truth_gathering_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_transport_present": (
                run_state_payload.get("repair_plan_transport_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_status": (
                run_state_payload.get("repair_plan_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_decision": (
                run_state_payload.get("repair_plan_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_class": (
                run_state_payload.get("repair_plan_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_priority": (
                run_state_payload.get("repair_plan_priority")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_confidence": (
                run_state_payload.get("repair_plan_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_target_surface": (
                run_state_payload.get("repair_plan_target_surface")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_candidate_action": (
                run_state_payload.get("repair_plan_candidate_action")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_primary_reason": (
                run_state_payload.get("repair_plan_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_manual_required": (
                run_state_payload.get("repair_plan_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_replan_required": (
                run_state_payload.get("repair_plan_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_plan_truth_gathering_required": (
                run_state_payload.get("repair_plan_truth_gathering_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_present": (
                run_state_payload.get("repair_approval_binding_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_status": (
                run_state_payload.get("repair_approval_binding_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_decision": (
                run_state_payload.get("repair_approval_binding_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_scope": (
                run_state_payload.get("repair_approval_binding_scope")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_validity": (
                run_state_payload.get("repair_approval_binding_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_compatibility_status": (
                run_state_payload.get("repair_approval_binding_compatibility_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_primary_reason": (
                run_state_payload.get("repair_approval_binding_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_manual_required": (
                run_state_payload.get("repair_approval_binding_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_replan_required": (
                run_state_payload.get("repair_approval_binding_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_approval_binding_truth_gathering_required": (
                run_state_payload.get("repair_approval_binding_truth_gathering_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_gate_present": (
                run_state_payload.get("execution_authorization_gate_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_status": (
                run_state_payload.get("execution_authorization_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_decision": (
                run_state_payload.get("execution_authorization_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_scope": (
                run_state_payload.get("execution_authorization_scope")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_validity": (
                run_state_payload.get("execution_authorization_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_confidence": (
                run_state_payload.get("execution_authorization_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_primary_reason": (
                run_state_payload.get("execution_authorization_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_manual_required": (
                run_state_payload.get("execution_authorization_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_replan_required": (
                run_state_payload.get("execution_authorization_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_authorization_truth_gathering_required": (
                run_state_payload.get("execution_authorization_truth_gathering_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_bridge_present": (
                run_state_payload.get("bounded_execution_bridge_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_status": (
                run_state_payload.get("bounded_execution_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_decision": (
                run_state_payload.get("bounded_execution_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_scope": (
                run_state_payload.get("bounded_execution_scope")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_validity": (
                run_state_payload.get("bounded_execution_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_confidence": (
                run_state_payload.get("bounded_execution_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_primary_reason": (
                run_state_payload.get("bounded_execution_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_manual_required": (
                run_state_payload.get("bounded_execution_manual_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_replan_required": (
                run_state_payload.get("bounded_execution_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "bounded_execution_truth_gathering_required": (
                run_state_payload.get("bounded_execution_truth_gathering_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_contract_present": (
                run_state_payload.get("execution_result_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_status": (
                run_state_payload.get("execution_result_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_outcome": (
                run_state_payload.get("execution_result_outcome")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_validity": (
                run_state_payload.get("execution_result_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_confidence": (
                run_state_payload.get("execution_result_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_primary_reason": (
                run_state_payload.get("execution_result_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_attempted": (
                run_state_payload.get("execution_result_attempted")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_receipt_present": (
                run_state_payload.get("execution_result_receipt_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_output_present": (
                run_state_payload.get("execution_result_output_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "execution_result_manual_followup_required": (
                run_state_payload.get("execution_result_manual_followup_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "verification_closure_contract_present": (
                run_state_payload.get("verification_closure_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "verification_status": (
                run_state_payload.get("verification_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "verification_outcome": (
                run_state_payload.get("verification_outcome")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "verification_validity": (
                run_state_payload.get("verification_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "verification_confidence": (
                run_state_payload.get("verification_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "verification_primary_reason": (
                run_state_payload.get("verification_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_satisfaction_status": (
                run_state_payload.get("objective_satisfaction_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_satisfaction_status": (
                run_state_payload.get("completion_satisfaction_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "closure_status": (
                run_state_payload.get("closure_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "closure_decision": (
                run_state_payload.get("closure_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "objective_satisfied": (
                run_state_payload.get("objective_satisfied")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completion_satisfied": (
                run_state_payload.get("completion_satisfied")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "safely_closable": (
                run_state_payload.get("safely_closable")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "manual_closure_required": (
                run_state_payload.get("manual_closure_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "closure_followup_required": (
                run_state_payload.get("closure_followup_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "external_truth_required": (
                run_state_payload.get("external_truth_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_reentry_loop_contract_present": (
                run_state_payload.get("retry_reentry_loop_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_loop_status": (
                run_state_payload.get("retry_loop_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_loop_decision": (
                run_state_payload.get("retry_loop_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_loop_validity": (
                run_state_payload.get("retry_loop_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_loop_confidence": (
                run_state_payload.get("retry_loop_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_primary_reason": (
                run_state_payload.get("loop_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "attempt_count": (
                run_state_payload.get("attempt_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "max_attempt_count": (
                run_state_payload.get("max_attempt_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reentry_count": (
                run_state_payload.get("reentry_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "max_reentry_count": (
                run_state_payload.get("max_reentry_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_count": (
                run_state_payload.get("same_failure_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "max_same_failure_count": (
                run_state_payload.get("max_same_failure_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_allowed": (
                run_state_payload.get("retry_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reentry_allowed": (
                run_state_payload.get("reentry_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_exhausted": (
                run_state_payload.get("retry_exhausted")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "reentry_exhausted": (
                run_state_payload.get("reentry_exhausted")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_exhausted": (
                run_state_payload.get("same_failure_exhausted")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "terminal_stop_required": (
                run_state_payload.get("terminal_stop_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "manual_escalation_required": (
                run_state_payload.get("manual_escalation_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "replan_required": (
                run_state_payload.get("replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "recollect_required": (
                run_state_payload.get("recollect_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_lane_retry_allowed": (
                run_state_payload.get("same_lane_retry_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "repair_retry_allowed": (
                run_state_payload.get("repair_retry_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "no_progress_stop_required": (
                run_state_payload.get("no_progress_stop_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "endgame_closure_contract_present": (
                run_state_payload.get("endgame_closure_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "endgame_closure_status": (
                run_state_payload.get("endgame_closure_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "endgame_closure_outcome": (
                run_state_payload.get("endgame_closure_outcome")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "endgame_closure_validity": (
                run_state_payload.get("endgame_closure_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "endgame_closure_confidence": (
                run_state_payload.get("endgame_closure_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "final_closure_class": (
                run_state_payload.get("final_closure_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "terminal_stop_class": (
                run_state_payload.get("terminal_stop_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "closure_resolution_status": (
                run_state_payload.get("closure_resolution_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "endgame_primary_reason": (
                run_state_payload.get("endgame_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "safely_closed": (
                run_state_payload.get("safely_closed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "completed_but_not_closed": (
                run_state_payload.get("completed_but_not_closed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "rollback_complete_but_not_closed": (
                run_state_payload.get("rollback_complete_but_not_closed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "manual_closure_only": (
                run_state_payload.get("manual_closure_only")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "external_truth_pending": (
                run_state_payload.get("external_truth_pending")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "closure_unresolved": (
                run_state_payload.get("closure_unresolved")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "terminal_success": (
                run_state_payload.get("terminal_success")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "terminal_non_success": (
                run_state_payload.get("terminal_non_success")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "operator_followup_required": (
                run_state_payload.get("operator_followup_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "further_retry_allowed": (
                run_state_payload.get("further_retry_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "further_reentry_allowed": (
                run_state_payload.get("further_reentry_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_hardening_contract_present": (
                run_state_payload.get("loop_hardening_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_hardening_status": (
                run_state_payload.get("loop_hardening_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_hardening_decision": (
                run_state_payload.get("loop_hardening_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_hardening_validity": (
                run_state_payload.get("loop_hardening_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_hardening_confidence": (
                run_state_payload.get("loop_hardening_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "loop_hardening_primary_reason": (
                run_state_payload.get("loop_hardening_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_signature": (
                run_state_payload.get("same_failure_signature")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_bucket": (
                run_state_payload.get("same_failure_bucket")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_persistence": (
                run_state_payload.get("same_failure_persistence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "no_progress_status": (
                run_state_payload.get("no_progress_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "oscillation_status": (
                run_state_payload.get("oscillation_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_freeze_status": (
                run_state_payload.get("retry_freeze_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_detected": (
                run_state_payload.get("same_failure_detected")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "same_failure_stop_required": (
                run_state_payload.get("same_failure_stop_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "no_progress_detected": (
                run_state_payload.get("no_progress_detected")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "oscillation_detected": (
                run_state_payload.get("oscillation_detected")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "unstable_loop_detected": (
                run_state_payload.get("unstable_loop_detected")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "retry_freeze_required": (
                run_state_payload.get("retry_freeze_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "cool_down_required": (
                run_state_payload.get("cool_down_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "forced_manual_escalation_required": (
                run_state_payload.get("forced_manual_escalation_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "hardening_stop_required": (
                run_state_payload.get("hardening_stop_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_stabilization_contract_present": (
                run_state_payload.get("lane_stabilization_contract_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_status": (
                run_state_payload.get("lane_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_decision": (
                run_state_payload.get("lane_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_validity": (
                run_state_payload.get("lane_validity")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_confidence": (
                run_state_payload.get("lane_confidence")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "current_lane": (
                run_state_payload.get("current_lane")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "target_lane": (
                run_state_payload.get("target_lane")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_transition_status": (
                run_state_payload.get("lane_transition_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_transition_decision": (
                run_state_payload.get("lane_transition_decision")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_preconditions_status": (
                run_state_payload.get("lane_preconditions_status")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_retry_policy_class": (
                run_state_payload.get("lane_retry_policy_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_verification_policy_class": (
                run_state_payload.get("lane_verification_policy_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_escalation_policy_class": (
                run_state_payload.get("lane_escalation_policy_class")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_attempt_budget": (
                run_state_payload.get("lane_attempt_budget")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_reentry_budget": (
                run_state_payload.get("lane_reentry_budget")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_transition_count": (
                run_state_payload.get("lane_transition_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "max_lane_transition_count": (
                run_state_payload.get("max_lane_transition_count")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_primary_reason": (
                run_state_payload.get("lane_primary_reason")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_valid": (
                run_state_payload.get("lane_valid")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_mismatch_detected": (
                run_state_payload.get("lane_mismatch_detected")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_transition_required": (
                run_state_payload.get("lane_transition_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_transition_allowed": (
                run_state_payload.get("lane_transition_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_transition_blocked": (
                run_state_payload.get("lane_transition_blocked")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_stop_required": (
                run_state_payload.get("lane_stop_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_manual_review_required": (
                run_state_payload.get("lane_manual_review_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_replan_required": (
                run_state_payload.get("lane_replan_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_truth_gathering_required": (
                run_state_payload.get("lane_truth_gathering_required")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "lane_execution_allowed": (
                run_state_payload.get("lane_execution_allowed")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "observability_rollup_present": (
                run_state_payload.get("observability_rollup_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "failure_bucketing_hardening_present": (
                run_state_payload.get("failure_bucketing_hardening_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "artifact_retention_present": (
                run_state_payload.get("artifact_retention_present")
                if isinstance(run_state_payload, dict)
                else None
            ),
            "fleet_safety_control_present": (
                run_state_payload.get("fleet_safety_control_present")
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
                "objective_contract",
                "completion_contract",
                "approval_transport",
                "reconcile_contract",
                "repair_suggestion_contract",
                "repair_plan_transport",
                "repair_approval_binding",
                "execution_authorization_gate",
                "bounded_execution_bridge",
                "execution_result_contract",
                "verification_closure_contract",
                "retry_reentry_loop_contract",
                "endgame_closure_contract",
                "loop_hardening_contract",
                "lane_stabilization_contract",
                "observability_rollup_contract",
                "failure_bucket_rollup",
                "fleet_run_rollup",
                "failure_bucketing_hardening_contract",
                "retention_manifest",
                "artifact_retention_contract",
                "fleet_safety_control_contract",
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
        objective_contract = lifecycle.get("objective_contract")
        completion_contract = lifecycle.get("completion_contract")
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
                    "lifecycle.objective_contract_present",
                    run_state.get("objective_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_id",
                    run_state.get("objective_id"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_summary",
                    run_state.get("objective_summary"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_type",
                    run_state.get("objective_type"),
                )
            )
            rows.append(
                line(
                    "lifecycle.requested_outcome",
                    run_state.get("requested_outcome"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_acceptance_status",
                    run_state.get("objective_acceptance_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_required_artifacts_status",
                    run_state.get("objective_required_artifacts_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_scope_status",
                    run_state.get("objective_scope_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_contract_status",
                    run_state.get("objective_contract_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_contract_blocked_reason",
                    run_state.get("objective_contract_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_contract_present",
                    run_state.get("completion_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_status",
                    run_state.get("completion_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.done_status",
                    run_state.get("done_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.safe_closure_status",
                    run_state.get("safe_closure_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_evidence_status",
                    run_state.get("completion_evidence_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_blocked_reason",
                    run_state.get("completion_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_manual_required",
                    run_state.get("completion_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_replan_required",
                    run_state.get("completion_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_lifecycle_alignment_status",
                    run_state.get("completion_lifecycle_alignment_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_transport_present",
                    run_state.get("approval_transport_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_status",
                    run_state.get("approval_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_decision",
                    run_state.get("approval_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_scope",
                    run_state.get("approval_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approved_action",
                    run_state.get("approved_action"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_required",
                    run_state.get("approval_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_transport_status",
                    run_state.get("approval_transport_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_compatibility_status",
                    run_state.get("approval_compatibility_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_blocked_reason",
                    run_state.get("approval_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_contract_present",
                    run_state.get("reconcile_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_status",
                    run_state.get("reconcile_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_decision",
                    run_state.get("reconcile_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_alignment_status",
                    run_state.get("reconcile_alignment_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_primary_mismatch",
                    run_state.get("reconcile_primary_mismatch"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_blocked_reason",
                    run_state.get("reconcile_blocked_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_waiting_on_truth",
                    run_state.get("reconcile_waiting_on_truth"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_manual_required",
                    run_state.get("reconcile_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_replan_required",
                    run_state.get("reconcile_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_contract_present",
                    run_state.get("repair_suggestion_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_status",
                    run_state.get("repair_suggestion_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_decision",
                    run_state.get("repair_suggestion_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_class",
                    run_state.get("repair_suggestion_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_priority",
                    run_state.get("repair_suggestion_priority"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_confidence",
                    run_state.get("repair_suggestion_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_primary_reason",
                    run_state.get("repair_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_manual_required",
                    run_state.get("repair_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_replan_required",
                    run_state.get("repair_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_truth_gathering_required",
                    run_state.get("repair_truth_gathering_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_transport_present",
                    run_state.get("repair_plan_transport_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_status",
                    run_state.get("repair_plan_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_decision",
                    run_state.get("repair_plan_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_class",
                    run_state.get("repair_plan_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_priority",
                    run_state.get("repair_plan_priority"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_confidence",
                    run_state.get("repair_plan_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_target_surface",
                    run_state.get("repair_plan_target_surface"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_candidate_action",
                    run_state.get("repair_plan_candidate_action"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_primary_reason",
                    run_state.get("repair_plan_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_manual_required",
                    run_state.get("repair_plan_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_replan_required",
                    run_state.get("repair_plan_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_truth_gathering_required",
                    run_state.get("repair_plan_truth_gathering_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_present",
                    run_state.get("repair_approval_binding_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_status",
                    run_state.get("repair_approval_binding_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_decision",
                    run_state.get("repair_approval_binding_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_scope",
                    run_state.get("repair_approval_binding_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_validity",
                    run_state.get("repair_approval_binding_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_compatibility_status",
                    run_state.get("repair_approval_binding_compatibility_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_primary_reason",
                    run_state.get("repair_approval_binding_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_manual_required",
                    run_state.get("repair_approval_binding_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_replan_required",
                    run_state.get("repair_approval_binding_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_truth_gathering_required",
                    run_state.get("repair_approval_binding_truth_gathering_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_gate_present",
                    run_state.get("execution_authorization_gate_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_status",
                    run_state.get("execution_authorization_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_decision",
                    run_state.get("execution_authorization_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_scope",
                    run_state.get("execution_authorization_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_validity",
                    run_state.get("execution_authorization_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_confidence",
                    run_state.get("execution_authorization_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_primary_reason",
                    run_state.get("execution_authorization_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_manual_required",
                    run_state.get("execution_authorization_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_replan_required",
                    run_state.get("execution_authorization_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_truth_gathering_required",
                    run_state.get("execution_authorization_truth_gathering_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_bridge_present",
                    run_state.get("bounded_execution_bridge_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_status",
                    run_state.get("bounded_execution_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_decision",
                    run_state.get("bounded_execution_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_scope",
                    run_state.get("bounded_execution_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_validity",
                    run_state.get("bounded_execution_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_confidence",
                    run_state.get("bounded_execution_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_primary_reason",
                    run_state.get("bounded_execution_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_manual_required",
                    run_state.get("bounded_execution_manual_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_replan_required",
                    run_state.get("bounded_execution_replan_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_truth_gathering_required",
                    run_state.get("bounded_execution_truth_gathering_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_contract_present",
                    run_state.get("execution_result_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_status",
                    run_state.get("execution_result_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_outcome",
                    run_state.get("execution_result_outcome"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_validity",
                    run_state.get("execution_result_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_confidence",
                    run_state.get("execution_result_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_primary_reason",
                    run_state.get("execution_result_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_attempted",
                    run_state.get("execution_result_attempted"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_receipt_present",
                    run_state.get("execution_result_receipt_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_output_present",
                    run_state.get("execution_result_output_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_manual_followup_required",
                    run_state.get("execution_result_manual_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.verification_closure_contract_present",
                    run_state.get("verification_closure_contract_present"),
                )
            )
            rows.append(line("lifecycle.verification_status", run_state.get("verification_status")))
            rows.append(line("lifecycle.verification_outcome", run_state.get("verification_outcome")))
            rows.append(line("lifecycle.verification_validity", run_state.get("verification_validity")))
            rows.append(
                line("lifecycle.verification_confidence", run_state.get("verification_confidence"))
            )
            rows.append(
                line(
                    "lifecycle.verification_primary_reason",
                    run_state.get("verification_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_satisfaction_status",
                    run_state.get("objective_satisfaction_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_satisfaction_status",
                    run_state.get("completion_satisfaction_status"),
                )
            )
            rows.append(line("lifecycle.closure_status_overlay", run_state.get("closure_status")))
            rows.append(line("lifecycle.closure_decision_overlay", run_state.get("closure_decision")))
            rows.append(line("lifecycle.objective_satisfied", run_state.get("objective_satisfied")))
            rows.append(line("lifecycle.completion_satisfied", run_state.get("completion_satisfied")))
            rows.append(line("lifecycle.safely_closable_overlay", run_state.get("safely_closable")))
            rows.append(
                line(
                    "lifecycle.manual_closure_required_overlay",
                    run_state.get("manual_closure_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.closure_followup_required_overlay",
                    run_state.get("closure_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.external_truth_required_overlay",
                    run_state.get("external_truth_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_reentry_loop_contract_present",
                    run_state.get("retry_reentry_loop_contract_present"),
                )
            )
            rows.append(line("lifecycle.retry_loop_status", run_state.get("retry_loop_status")))
            rows.append(line("lifecycle.retry_loop_decision", run_state.get("retry_loop_decision")))
            rows.append(line("lifecycle.retry_loop_validity", run_state.get("retry_loop_validity")))
            rows.append(line("lifecycle.retry_loop_confidence", run_state.get("retry_loop_confidence")))
            rows.append(line("lifecycle.loop_primary_reason", run_state.get("loop_primary_reason")))
            rows.append(line("lifecycle.attempt_count", run_state.get("attempt_count")))
            rows.append(line("lifecycle.max_attempt_count", run_state.get("max_attempt_count")))
            rows.append(line("lifecycle.reentry_count", run_state.get("reentry_count")))
            rows.append(line("lifecycle.max_reentry_count", run_state.get("max_reentry_count")))
            rows.append(line("lifecycle.same_failure_count", run_state.get("same_failure_count")))
            rows.append(
                line("lifecycle.max_same_failure_count", run_state.get("max_same_failure_count"))
            )
            rows.append(line("lifecycle.retry_allowed", run_state.get("retry_allowed")))
            rows.append(line("lifecycle.reentry_allowed", run_state.get("reentry_allowed")))
            rows.append(line("lifecycle.retry_exhausted", run_state.get("retry_exhausted")))
            rows.append(line("lifecycle.reentry_exhausted", run_state.get("reentry_exhausted")))
            rows.append(
                line("lifecycle.same_failure_exhausted", run_state.get("same_failure_exhausted"))
            )
            rows.append(
                line("lifecycle.terminal_stop_required", run_state.get("terminal_stop_required"))
            )
            rows.append(
                line(
                    "lifecycle.manual_escalation_required",
                    run_state.get("manual_escalation_required"),
                )
            )
            rows.append(line("lifecycle.replan_required_overlay", run_state.get("replan_required")))
            rows.append(line("lifecycle.recollect_required", run_state.get("recollect_required")))
            rows.append(
                line("lifecycle.same_lane_retry_allowed", run_state.get("same_lane_retry_allowed"))
            )
            rows.append(
                line("lifecycle.repair_retry_allowed", run_state.get("repair_retry_allowed"))
            )
            rows.append(
                line(
                    "lifecycle.no_progress_stop_required",
                    run_state.get("no_progress_stop_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_contract_present",
                    run_state.get("endgame_closure_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_status",
                    run_state.get("endgame_closure_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_outcome",
                    run_state.get("endgame_closure_outcome"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_validity",
                    run_state.get("endgame_closure_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_confidence",
                    run_state.get("endgame_closure_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.final_closure_class",
                    run_state.get("final_closure_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.terminal_stop_class",
                    run_state.get("terminal_stop_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.closure_resolution_status",
                    run_state.get("closure_resolution_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_primary_reason",
                    run_state.get("endgame_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.safely_closed_overlay",
                    run_state.get("safely_closed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completed_but_not_closed_overlay",
                    run_state.get("completed_but_not_closed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.rollback_complete_but_not_closed_overlay",
                    run_state.get("rollback_complete_but_not_closed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.manual_closure_only_overlay",
                    run_state.get("manual_closure_only"),
                )
            )
            rows.append(
                line(
                    "lifecycle.external_truth_pending_overlay",
                    run_state.get("external_truth_pending"),
                )
            )
            rows.append(
                line(
                    "lifecycle.closure_unresolved_overlay",
                    run_state.get("closure_unresolved"),
                )
            )
            rows.append(
                line(
                    "lifecycle.terminal_success_overlay",
                    run_state.get("terminal_success"),
                )
            )
            rows.append(
                line(
                    "lifecycle.terminal_non_success_overlay",
                    run_state.get("terminal_non_success"),
                )
            )
            rows.append(
                line(
                    "lifecycle.operator_followup_required_overlay",
                    run_state.get("operator_followup_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.further_retry_allowed_overlay",
                    run_state.get("further_retry_allowed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.further_reentry_allowed_overlay",
                    run_state.get("further_reentry_allowed"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_contract_present",
                    run_state.get("loop_hardening_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_status",
                    run_state.get("loop_hardening_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_decision",
                    run_state.get("loop_hardening_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_validity",
                    run_state.get("loop_hardening_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_confidence",
                    run_state.get("loop_hardening_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_primary_reason",
                    run_state.get("loop_hardening_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.same_failure_signature_overlay",
                    run_state.get("same_failure_signature"),
                )
            )
            rows.append(
                line(
                    "lifecycle.same_failure_bucket_overlay",
                    run_state.get("same_failure_bucket"),
                )
            )
            rows.append(
                line(
                    "lifecycle.same_failure_persistence_overlay",
                    run_state.get("same_failure_persistence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.no_progress_status_overlay",
                    run_state.get("no_progress_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.oscillation_status_overlay",
                    run_state.get("oscillation_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_freeze_status_overlay",
                    run_state.get("retry_freeze_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.hardening_stop_required_overlay",
                    run_state.get("hardening_stop_required"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_stabilization_contract_present",
                    run_state.get("lane_stabilization_contract_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.observability_rollup_present",
                    run_state.get("observability_rollup_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.failure_bucketing_hardening_present",
                    run_state.get("failure_bucketing_hardening_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.artifact_retention_present",
                    run_state.get("artifact_retention_present"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_safety_control_present",
                    run_state.get("fleet_safety_control_present"),
                )
            )
            rows.append(line("lifecycle.lane_status", run_state.get("lane_status")))
            rows.append(line("lifecycle.lane_decision", run_state.get("lane_decision")))
            rows.append(line("lifecycle.lane_validity", run_state.get("lane_validity")))
            rows.append(line("lifecycle.lane_confidence", run_state.get("lane_confidence")))
            rows.append(line("lifecycle.current_lane_overlay", run_state.get("current_lane")))
            rows.append(line("lifecycle.target_lane_overlay", run_state.get("target_lane")))
            rows.append(
                line(
                    "lifecycle.lane_transition_status_overlay",
                    run_state.get("lane_transition_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_transition_decision_overlay",
                    run_state.get("lane_transition_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_retry_policy_class_overlay",
                    run_state.get("lane_retry_policy_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_verification_policy_class_overlay",
                    run_state.get("lane_verification_policy_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_escalation_policy_class_overlay",
                    run_state.get("lane_escalation_policy_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_primary_reason_overlay",
                    run_state.get("lane_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_execution_allowed_overlay",
                    run_state.get("lane_execution_allowed"),
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
        if isinstance(objective_contract, dict):
            rows.append(
                line(
                    "lifecycle.objective_contract_status_artifact",
                    objective_contract.get("objective_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_contract_source_status_artifact",
                    objective_contract.get("objective_source_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_acceptance_status_artifact",
                    objective_contract.get("acceptance_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_scope_status_artifact",
                    objective_contract.get("scope_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_required_artifacts_status_artifact",
                    objective_contract.get("required_artifacts_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_acceptance_criteria_total",
                    objective_contract.get("acceptance_criteria_total"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_acceptance_criteria_defined",
                    objective_contract.get("acceptance_criteria_defined"),
                )
            )
            rows.append(
                line(
                    "lifecycle.objective_required_artifacts_total",
                    objective_contract.get("required_artifacts_total"),
                )
            )
        if isinstance(completion_contract, dict):
            rows.append(
                line(
                    "lifecycle.completion_contract_status_artifact",
                    completion_contract.get("completion_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_done_status_artifact",
                    completion_contract.get("done_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_safe_closure_status_artifact",
                    completion_contract.get("safe_closure_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_evidence_status_artifact",
                    completion_contract.get("completion_evidence_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_closure_decision_artifact",
                    completion_contract.get("closure_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_lifecycle_alignment_status_artifact",
                    completion_contract.get("lifecycle_alignment_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_required_evidence_total",
                    completion_contract.get("required_evidence_total"),
                )
            )
            rows.append(
                line(
                    "lifecycle.completion_missing_evidence_total",
                    completion_contract.get("missing_evidence_total"),
                )
            )
        approval_transport = lifecycle.get("approval_transport")
        if isinstance(approval_transport, dict):
            rows.append(
                line(
                    "lifecycle.approval_status_artifact",
                    approval_transport.get("approval_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_decision_artifact",
                    approval_transport.get("approval_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_scope_artifact",
                    approval_transport.get("approval_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_transport_status_artifact",
                    approval_transport.get("approval_transport_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_compatibility_status_artifact",
                    approval_transport.get("approval_compatibility_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.approval_blocked_reason_artifact",
                    approval_transport.get("approval_blocked_reason"),
                )
            )
        reconcile_contract = lifecycle.get("reconcile_contract")
        if isinstance(reconcile_contract, dict):
            rows.append(
                line(
                    "lifecycle.reconcile_status_artifact",
                    reconcile_contract.get("reconcile_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_decision_artifact",
                    reconcile_contract.get("reconcile_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_alignment_status_artifact",
                    reconcile_contract.get("reconcile_alignment_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_primary_mismatch_artifact",
                    reconcile_contract.get("reconcile_primary_mismatch"),
                )
            )
            rows.append(
                line(
                    "lifecycle.reconcile_transport_status_artifact",
                    reconcile_contract.get("reconcile_transport_status"),
                )
            )
        repair_suggestion_contract = lifecycle.get("repair_suggestion_contract")
        if isinstance(repair_suggestion_contract, dict):
            rows.append(
                line(
                    "lifecycle.repair_suggestion_status_artifact",
                    repair_suggestion_contract.get("repair_suggestion_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_decision_artifact",
                    repair_suggestion_contract.get("repair_suggestion_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_class_artifact",
                    repair_suggestion_contract.get("repair_suggestion_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_suggestion_priority_artifact",
                    repair_suggestion_contract.get("repair_suggestion_priority"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_primary_reason_artifact",
                    repair_suggestion_contract.get("repair_primary_reason"),
                )
            )
        repair_plan_transport = lifecycle.get("repair_plan_transport")
        if isinstance(repair_plan_transport, dict):
            rows.append(
                line(
                    "lifecycle.repair_plan_status_artifact",
                    repair_plan_transport.get("repair_plan_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_decision_artifact",
                    repair_plan_transport.get("repair_plan_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_class_artifact",
                    repair_plan_transport.get("repair_plan_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_priority_artifact",
                    repair_plan_transport.get("repair_plan_priority"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_plan_primary_reason_artifact",
                    repair_plan_transport.get("repair_plan_primary_reason"),
                )
            )
        repair_approval_binding = lifecycle.get("repair_approval_binding")
        if isinstance(repair_approval_binding, dict):
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_status_artifact",
                    repair_approval_binding.get("repair_approval_binding_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_decision_artifact",
                    repair_approval_binding.get("repair_approval_binding_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_validity_artifact",
                    repair_approval_binding.get("repair_approval_binding_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_compatibility_status_artifact",
                    repair_approval_binding.get("repair_approval_binding_compatibility_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.repair_approval_binding_primary_reason_artifact",
                    repair_approval_binding.get("repair_approval_binding_primary_reason"),
                )
            )
        execution_authorization_gate = lifecycle.get("execution_authorization_gate")
        if isinstance(execution_authorization_gate, dict):
            rows.append(
                line(
                    "lifecycle.execution_authorization_status_artifact",
                    execution_authorization_gate.get("execution_authorization_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_decision_artifact",
                    execution_authorization_gate.get("execution_authorization_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_validity_artifact",
                    execution_authorization_gate.get("execution_authorization_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_confidence_artifact",
                    execution_authorization_gate.get("execution_authorization_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_authorization_primary_reason_artifact",
                    execution_authorization_gate.get("execution_authorization_primary_reason"),
                )
            )
        bounded_execution_bridge = lifecycle.get("bounded_execution_bridge")
        if isinstance(bounded_execution_bridge, dict):
            rows.append(
                line(
                    "lifecycle.bounded_execution_status_artifact",
                    bounded_execution_bridge.get("bounded_execution_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_decision_artifact",
                    bounded_execution_bridge.get("bounded_execution_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_validity_artifact",
                    bounded_execution_bridge.get("bounded_execution_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_confidence_artifact",
                    bounded_execution_bridge.get("bounded_execution_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.bounded_execution_primary_reason_artifact",
                    bounded_execution_bridge.get("bounded_execution_primary_reason"),
                )
            )
        execution_result_contract = lifecycle.get("execution_result_contract")
        if isinstance(execution_result_contract, dict):
            rows.append(
                line(
                    "lifecycle.execution_result_status_artifact",
                    execution_result_contract.get("execution_result_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_outcome_artifact",
                    execution_result_contract.get("execution_result_outcome"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_validity_artifact",
                    execution_result_contract.get("execution_result_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_confidence_artifact",
                    execution_result_contract.get("execution_result_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.execution_result_primary_reason_artifact",
                    execution_result_contract.get("execution_result_primary_reason"),
                )
            )
        verification_closure_contract = lifecycle.get("verification_closure_contract")
        if isinstance(verification_closure_contract, dict):
            rows.append(
                line(
                    "lifecycle.verification_status_artifact",
                    verification_closure_contract.get("verification_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.verification_outcome_artifact",
                    verification_closure_contract.get("verification_outcome"),
                )
            )
            rows.append(
                line(
                    "lifecycle.verification_validity_artifact",
                    verification_closure_contract.get("verification_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.verification_confidence_artifact",
                    verification_closure_contract.get("verification_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.verification_primary_reason_artifact",
                    verification_closure_contract.get("verification_primary_reason"),
                )
            )
            rows.append(
                line(
                    "lifecycle.closure_status_artifact",
                    verification_closure_contract.get("closure_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.closure_decision_artifact",
                    verification_closure_contract.get("closure_decision"),
                )
            )
        retry_reentry_loop_contract = lifecycle.get("retry_reentry_loop_contract")
        if isinstance(retry_reentry_loop_contract, dict):
            rows.append(
                line(
                    "lifecycle.retry_loop_status_artifact",
                    retry_reentry_loop_contract.get("retry_loop_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_loop_decision_artifact",
                    retry_reentry_loop_contract.get("retry_loop_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_loop_validity_artifact",
                    retry_reentry_loop_contract.get("retry_loop_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_loop_confidence_artifact",
                    retry_reentry_loop_contract.get("retry_loop_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_loop_primary_reason_artifact",
                    retry_reentry_loop_contract.get("loop_primary_reason"),
                )
            )
        endgame_closure_contract = lifecycle.get("endgame_closure_contract")
        if isinstance(endgame_closure_contract, dict):
            rows.append(
                line(
                    "lifecycle.endgame_closure_status_artifact",
                    endgame_closure_contract.get("endgame_closure_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_outcome_artifact",
                    endgame_closure_contract.get("endgame_closure_outcome"),
                )
            )
            rows.append(
                line(
                    "lifecycle.final_closure_class_artifact",
                    endgame_closure_contract.get("final_closure_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.terminal_stop_class_artifact",
                    endgame_closure_contract.get("terminal_stop_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_primary_reason_artifact",
                    endgame_closure_contract.get("endgame_primary_reason"),
                )
            )
        loop_hardening_contract = lifecycle.get("loop_hardening_contract")
        if isinstance(loop_hardening_contract, dict):
            rows.append(
                line(
                    "lifecycle.loop_hardening_status_artifact",
                    loop_hardening_contract.get("loop_hardening_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_decision_artifact",
                    loop_hardening_contract.get("loop_hardening_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_validity_artifact",
                    loop_hardening_contract.get("loop_hardening_validity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_confidence_artifact",
                    loop_hardening_contract.get("loop_hardening_confidence"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_primary_reason_artifact",
                    loop_hardening_contract.get("loop_hardening_primary_reason"),
                )
            )
        lane_stabilization_contract = lifecycle.get("lane_stabilization_contract")
        if isinstance(lane_stabilization_contract, dict):
            rows.append(
                line(
                    "lifecycle.lane_status_artifact",
                    lane_stabilization_contract.get("lane_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_decision_artifact",
                    lane_stabilization_contract.get("lane_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.current_lane_artifact",
                    lane_stabilization_contract.get("current_lane"),
                )
            )
            rows.append(
                line(
                    "lifecycle.target_lane_artifact",
                    lane_stabilization_contract.get("target_lane"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_primary_reason_artifact",
                    lane_stabilization_contract.get("lane_primary_reason"),
                )
            )
        observability_rollup_contract = lifecycle.get("observability_rollup_contract")
        if isinstance(observability_rollup_contract, dict):
            rows.append(
                line(
                    "lifecycle.observability_status_artifact",
                    observability_rollup_contract.get("observability_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.observability_terminal_class_artifact",
                    observability_rollup_contract.get("run_terminal_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.observability_lane_artifact",
                    observability_rollup_contract.get("lane"),
                )
            )
            rows.append(
                line(
                    "lifecycle.observability_primary_reason_artifact",
                    observability_rollup_contract.get("observability_primary_reason"),
                )
            )
        failure_bucket_rollup = lifecycle.get("failure_bucket_rollup")
        if isinstance(failure_bucket_rollup, dict):
            rows.append(
                line(
                    "lifecycle.failure_bucket_status_artifact",
                    failure_bucket_rollup.get("failure_bucket_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.primary_failure_bucket_artifact",
                    failure_bucket_rollup.get("primary_failure_bucket"),
                )
            )
            rows.append(
                line(
                    "lifecycle.failure_bucket_primary_reason_artifact",
                    failure_bucket_rollup.get("failure_bucket_primary_reason"),
                )
            )
        fleet_run_rollup = lifecycle.get("fleet_run_rollup")
        if isinstance(fleet_run_rollup, dict):
            rows.append(
                line(
                    "lifecycle.fleet_terminal_class_artifact",
                    fleet_run_rollup.get("fleet_terminal_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_primary_failure_bucket_artifact",
                    fleet_run_rollup.get("fleet_primary_failure_bucket"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_observability_status_artifact",
                    fleet_run_rollup.get("fleet_observability_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_primary_reason_artifact",
                    fleet_run_rollup.get("fleet_primary_reason"),
                )
            )
        failure_bucketing_hardening_contract = lifecycle.get(
            "failure_bucketing_hardening_contract"
        )
        if isinstance(failure_bucketing_hardening_contract, dict):
            rows.append(
                line(
                    "lifecycle.hardened_primary_failure_bucket_artifact",
                    failure_bucketing_hardening_contract.get("primary_failure_bucket"),
                )
            )
            rows.append(
                line(
                    "lifecycle.hardened_bucket_family_artifact",
                    failure_bucketing_hardening_contract.get("bucket_family"),
                )
            )
            rows.append(
                line(
                    "lifecycle.hardened_bucket_severity_artifact",
                    failure_bucketing_hardening_contract.get("bucket_severity"),
                )
            )
            rows.append(
                line(
                    "lifecycle.hardened_bucket_stability_artifact",
                    failure_bucketing_hardening_contract.get("bucket_stability_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.hardened_bucket_primary_reason_artifact",
                    failure_bucketing_hardening_contract.get(
                        "failure_bucketing_primary_reason"
                    ),
                )
            )
        artifact_retention_contract = lifecycle.get("artifact_retention_contract")
        if isinstance(artifact_retention_contract, dict):
            rows.append(
                line(
                    "lifecycle.artifact_retention_status_artifact",
                    artifact_retention_contract.get("artifact_retention_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retention_policy_class_artifact",
                    artifact_retention_contract.get("retention_policy_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retention_compaction_class_artifact",
                    artifact_retention_contract.get("retention_compaction_class"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retention_primary_reason_artifact",
                    artifact_retention_contract.get("retention_primary_reason"),
                )
            )
        fleet_safety_control_contract = lifecycle.get("fleet_safety_control_contract")
        if isinstance(fleet_safety_control_contract, dict):
            rows.append(
                line(
                    "lifecycle.fleet_safety_status_artifact",
                    fleet_safety_control_contract.get("fleet_safety_status"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_safety_decision_artifact",
                    fleet_safety_control_contract.get("fleet_safety_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_restart_decision_artifact",
                    fleet_safety_control_contract.get("fleet_restart_decision"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_safety_scope_artifact",
                    fleet_safety_control_contract.get("fleet_safety_scope"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_safety_primary_reason_artifact",
                    fleet_safety_control_contract.get("fleet_safety_primary_reason"),
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
            rows.append(line("lifecycle.objective_contract_path", paths.get("objective_contract")))
            rows.append(line("lifecycle.completion_contract_path", paths.get("completion_contract")))
            rows.append(line("lifecycle.approval_transport_path", paths.get("approval_transport")))
            rows.append(line("lifecycle.reconcile_contract_path", paths.get("reconcile_contract")))
            rows.append(line("lifecycle.repair_suggestion_contract_path", paths.get("repair_suggestion_contract")))
            rows.append(line("lifecycle.repair_plan_transport_path", paths.get("repair_plan_transport")))
            rows.append(line("lifecycle.repair_approval_binding_path", paths.get("repair_approval_binding")))
            rows.append(line("lifecycle.execution_authorization_gate_path", paths.get("execution_authorization_gate")))
            rows.append(line("lifecycle.bounded_execution_bridge_path", paths.get("bounded_execution_bridge")))
            rows.append(line("lifecycle.execution_result_contract_path", paths.get("execution_result_contract")))
            rows.append(
                line(
                    "lifecycle.verification_closure_contract_path",
                    paths.get("verification_closure_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retry_reentry_loop_contract_path",
                    paths.get("retry_reentry_loop_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.endgame_closure_contract_path",
                    paths.get("endgame_closure_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.loop_hardening_contract_path",
                    paths.get("loop_hardening_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.lane_stabilization_contract_path",
                    paths.get("lane_stabilization_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.observability_rollup_contract_path",
                    paths.get("observability_rollup_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.failure_bucket_rollup_path",
                    paths.get("failure_bucket_rollup"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_run_rollup_path",
                    paths.get("fleet_run_rollup"),
                )
            )
            rows.append(
                line(
                    "lifecycle.failure_bucketing_hardening_contract_path",
                    paths.get("failure_bucketing_hardening_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.retention_manifest_path",
                    paths.get("retention_manifest"),
                )
            )
            rows.append(
                line(
                    "lifecycle.artifact_retention_contract_path",
                    paths.get("artifact_retention_contract"),
                )
            )
            rows.append(
                line(
                    "lifecycle.fleet_safety_control_contract_path",
                    paths.get("fleet_safety_control_contract"),
                )
            )

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

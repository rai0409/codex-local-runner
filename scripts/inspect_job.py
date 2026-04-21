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
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface  # noqa: E402
from automation.orchestration.bounded_execution_bridge import (  # noqa: E402
    build_bounded_execution_bridge_run_state_summary_surface,
)
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface  # noqa: E402
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
            **failure_bucketing_hardening_surface,
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
    objective_contract_payload = _read_json_object(str(objective_contract_path))
    completion_contract_payload = _read_json_object(str(completion_contract_path))
    approval_transport_payload = _read_json_object(str(approval_transport_path))
    reconcile_contract_payload = _read_json_object(str(reconcile_contract_path))
    repair_suggestion_contract_payload = _read_json_object(str(repair_suggestion_contract_path))
    repair_plan_transport_payload = _read_json_object(str(repair_plan_transport_path))
    repair_approval_binding_payload = _read_json_object(str(repair_approval_binding_path))
    execution_authorization_gate_payload = _read_json_object(str(execution_authorization_gate_path))
    bounded_execution_bridge_payload = _read_json_object(str(bounded_execution_bridge_path))
    execution_result_contract_payload = _read_json_object(str(execution_result_contract_path))
    verification_closure_contract_payload = _read_json_object(
        str(verification_closure_contract_path)
    )
    retry_reentry_loop_contract_payload = _read_json_object(
        str(retry_reentry_loop_contract_path)
    )
    endgame_closure_contract_payload = _read_json_object(
        str(endgame_closure_contract_path)
    )
    loop_hardening_contract_payload = _read_json_object(
        str(loop_hardening_contract_path)
    )
    lane_stabilization_contract_payload = _read_json_object(
        str(lane_stabilization_contract_path)
    )
    observability_rollup_contract_payload = _read_json_object(
        str(observability_rollup_contract_path)
    )
    failure_bucket_rollup_payload = _read_json_object(str(failure_bucket_rollup_path))
    fleet_run_rollup_payload = _read_json_object(str(fleet_run_rollup_path))
    failure_bucketing_hardening_contract_payload = _read_json_object(
        str(failure_bucketing_hardening_contract_path)
    )
    retention_manifest_payload = _read_json_object(str(retention_manifest_path))
    artifact_retention_contract_payload = _read_json_object(
        str(artifact_retention_contract_path)
    )
    fleet_safety_control_contract_payload = _read_json_object(
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
        "lifecycle_objective_contract_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_contract_present")),
        "lifecycle_objective_id: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_id")),
        "lifecycle_objective_summary: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_summary")),
        "lifecycle_objective_type: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_type")),
        "lifecycle_requested_outcome: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("requested_outcome")),
        "lifecycle_objective_acceptance_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_acceptance_status")),
        "lifecycle_objective_required_artifacts_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_required_artifacts_status")),
        "lifecycle_objective_scope_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_scope_status")),
        "lifecycle_objective_contract_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_contract_status")),
        "lifecycle_objective_contract_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_contract_blocked_reason")),
        "lifecycle_completion_contract_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_contract_present")),
        "lifecycle_completion_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_status")),
        "lifecycle_done_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("done_status")),
        "lifecycle_safe_closure_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("safe_closure_status")),
        "lifecycle_completion_evidence_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_evidence_status")),
        "lifecycle_completion_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_blocked_reason")),
        "lifecycle_completion_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_manual_required")),
        "lifecycle_completion_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_replan_required")),
        "lifecycle_completion_lifecycle_alignment_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_lifecycle_alignment_status")),
        "lifecycle_approval_transport_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_transport_present")),
        "lifecycle_approval_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_status")),
        "lifecycle_approval_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_decision")),
        "lifecycle_approval_scope: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_scope")),
        "lifecycle_approved_action: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approved_action")),
        "lifecycle_approval_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_required")),
        "lifecycle_approval_transport_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_transport_status")),
        "lifecycle_approval_compatibility_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_compatibility_status")),
        "lifecycle_approval_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("approval_blocked_reason")),
        "lifecycle_reconcile_contract_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_contract_present")),
        "lifecycle_reconcile_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_status")),
        "lifecycle_reconcile_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_decision")),
        "lifecycle_reconcile_alignment_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_alignment_status")),
        "lifecycle_reconcile_primary_mismatch: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_primary_mismatch")),
        "lifecycle_reconcile_blocked_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_blocked_reason")),
        "lifecycle_reconcile_waiting_on_truth: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_waiting_on_truth")),
        "lifecycle_reconcile_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_manual_required")),
        "lifecycle_reconcile_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reconcile_replan_required")),
        "lifecycle_repair_suggestion_contract_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_suggestion_contract_present")),
        "lifecycle_repair_suggestion_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_suggestion_status")),
        "lifecycle_repair_suggestion_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_suggestion_decision")),
        "lifecycle_repair_suggestion_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_suggestion_class")),
        "lifecycle_repair_suggestion_priority: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_suggestion_priority")),
        "lifecycle_repair_suggestion_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_suggestion_confidence")),
        "lifecycle_repair_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_primary_reason")),
        "lifecycle_repair_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_manual_required")),
        "lifecycle_repair_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_replan_required")),
        "lifecycle_repair_truth_gathering_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_truth_gathering_required")),
        "lifecycle_repair_plan_transport_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_transport_present")),
        "lifecycle_repair_plan_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_status")),
        "lifecycle_repair_plan_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_decision")),
        "lifecycle_repair_plan_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_class")),
        "lifecycle_repair_plan_priority: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_priority")),
        "lifecycle_repair_plan_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_confidence")),
        "lifecycle_repair_plan_target_surface: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_target_surface")),
        "lifecycle_repair_plan_candidate_action: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_candidate_action")),
        "lifecycle_repair_plan_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_primary_reason")),
        "lifecycle_repair_plan_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_manual_required")),
        "lifecycle_repair_plan_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_replan_required")),
        "lifecycle_repair_plan_truth_gathering_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_plan_truth_gathering_required")),
        "lifecycle_repair_approval_binding_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_present")),
        "lifecycle_repair_approval_binding_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_status")),
        "lifecycle_repair_approval_binding_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_decision")),
        "lifecycle_repair_approval_binding_scope: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_scope")),
        "lifecycle_repair_approval_binding_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_validity")),
        "lifecycle_repair_approval_binding_compatibility_status: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "repair_approval_binding_compatibility_status"
            )
        ),
        "lifecycle_repair_approval_binding_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_primary_reason")),
        "lifecycle_repair_approval_binding_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_manual_required")),
        "lifecycle_repair_approval_binding_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_approval_binding_replan_required")),
        "lifecycle_repair_approval_binding_truth_gathering_required: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "repair_approval_binding_truth_gathering_required"
            )
        ),
        "lifecycle_execution_authorization_gate_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_gate_present")),
        "lifecycle_execution_authorization_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_status")),
        "lifecycle_execution_authorization_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_decision")),
        "lifecycle_execution_authorization_scope: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_scope")),
        "lifecycle_execution_authorization_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_validity")),
        "lifecycle_execution_authorization_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_confidence")),
        "lifecycle_execution_authorization_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_primary_reason")),
        "lifecycle_execution_authorization_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_manual_required")),
        "lifecycle_execution_authorization_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_authorization_replan_required")),
        "lifecycle_execution_authorization_truth_gathering_required: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "execution_authorization_truth_gathering_required"
            )
        ),
        "lifecycle_bounded_execution_bridge_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_bridge_present")),
        "lifecycle_bounded_execution_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_status")),
        "lifecycle_bounded_execution_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_decision")),
        "lifecycle_bounded_execution_scope: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_scope")),
        "lifecycle_bounded_execution_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_validity")),
        "lifecycle_bounded_execution_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_confidence")),
        "lifecycle_bounded_execution_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_primary_reason")),
        "lifecycle_bounded_execution_manual_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_manual_required")),
        "lifecycle_bounded_execution_replan_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("bounded_execution_replan_required")),
        "lifecycle_bounded_execution_truth_gathering_required: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "bounded_execution_truth_gathering_required"
            )
        ),
        "lifecycle_execution_result_contract_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_contract_present")),
        "lifecycle_execution_result_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_status")),
        "lifecycle_execution_result_outcome: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_outcome")),
        "lifecycle_execution_result_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_validity")),
        "lifecycle_execution_result_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_confidence")),
        "lifecycle_execution_result_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_primary_reason")),
        "lifecycle_execution_result_attempted: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_attempted")),
        "lifecycle_execution_result_receipt_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_receipt_present")),
        "lifecycle_execution_result_output_present: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("execution_result_output_present")),
        "lifecycle_execution_result_manual_followup_required: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "execution_result_manual_followup_required"
            )
        ),
        "lifecycle_verification_closure_contract_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "verification_closure_contract_present"
            )
        ),
        "lifecycle_verification_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("verification_status")),
        "lifecycle_verification_outcome: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("verification_outcome")),
        "lifecycle_verification_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("verification_validity")),
        "lifecycle_verification_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("verification_confidence")),
        "lifecycle_verification_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("verification_primary_reason")),
        "lifecycle_objective_satisfaction_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("objective_satisfaction_status")),
        "lifecycle_completion_satisfaction_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completion_satisfaction_status")),
        "lifecycle_closure_decision_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("closure_decision")),
        "lifecycle_safely_closable_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("safely_closable")),
        "lifecycle_manual_closure_required_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("manual_closure_required")),
        "lifecycle_closure_followup_required_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("closure_followup_required")),
        "lifecycle_external_truth_required_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("external_truth_required")),
        "lifecycle_retry_reentry_loop_contract_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "retry_reentry_loop_contract_present"
            )
        ),
        "lifecycle_retry_loop_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_loop_status")),
        "lifecycle_retry_loop_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_loop_decision")),
        "lifecycle_retry_loop_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_loop_validity")),
        "lifecycle_retry_loop_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_loop_confidence")),
        "lifecycle_loop_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_primary_reason")),
        "lifecycle_attempt_count: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("attempt_count")),
        "lifecycle_max_attempt_count: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("max_attempt_count")),
        "lifecycle_reentry_count: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reentry_count")),
        "lifecycle_max_reentry_count: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("max_reentry_count")),
        "lifecycle_same_failure_count: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("same_failure_count")),
        "lifecycle_max_same_failure_count: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("max_same_failure_count")),
        "lifecycle_retry_allowed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_allowed")),
        "lifecycle_reentry_allowed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reentry_allowed")),
        "lifecycle_retry_exhausted: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_exhausted")),
        "lifecycle_reentry_exhausted: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("reentry_exhausted")),
        "lifecycle_same_failure_exhausted: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("same_failure_exhausted")),
        "lifecycle_terminal_stop_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("terminal_stop_required")),
        "lifecycle_manual_escalation_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("manual_escalation_required")),
        "lifecycle_replan_required_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("replan_required")),
        "lifecycle_recollect_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("recollect_required")),
        "lifecycle_same_lane_retry_allowed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("same_lane_retry_allowed")),
        "lifecycle_repair_retry_allowed: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("repair_retry_allowed")),
        "lifecycle_no_progress_stop_required: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("no_progress_stop_required")),
        "lifecycle_endgame_closure_contract_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "endgame_closure_contract_present"
            )
        ),
        "lifecycle_endgame_closure_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("endgame_closure_status")),
        "lifecycle_endgame_closure_outcome: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("endgame_closure_outcome")),
        "lifecycle_endgame_closure_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("endgame_closure_validity")),
        "lifecycle_endgame_closure_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("endgame_closure_confidence")),
        "lifecycle_final_closure_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("final_closure_class")),
        "lifecycle_terminal_stop_class: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("terminal_stop_class")),
        "lifecycle_closure_resolution_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("closure_resolution_status")),
        "lifecycle_endgame_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("endgame_primary_reason")),
        "lifecycle_safely_closed_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("safely_closed")),
        "lifecycle_completed_but_not_closed_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("completed_but_not_closed")),
        "lifecycle_rollback_complete_but_not_closed_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("rollback_complete_but_not_closed")),
        "lifecycle_manual_closure_only_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("manual_closure_only")),
        "lifecycle_external_truth_pending_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("external_truth_pending")),
        "lifecycle_closure_unresolved_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("closure_unresolved")),
        "lifecycle_terminal_success_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("terminal_success")),
        "lifecycle_terminal_non_success_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("terminal_non_success")),
        "lifecycle_operator_followup_required_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("operator_followup_required")),
        "lifecycle_further_retry_allowed_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("further_retry_allowed")),
        "lifecycle_further_reentry_allowed_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("further_reentry_allowed")),
        "lifecycle_loop_hardening_contract_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "loop_hardening_contract_present"
            )
        ),
        "lifecycle_loop_hardening_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_hardening_status")),
        "lifecycle_loop_hardening_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_hardening_decision")),
        "lifecycle_loop_hardening_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_hardening_validity")),
        "lifecycle_loop_hardening_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_hardening_confidence")),
        "lifecycle_loop_hardening_primary_reason: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("loop_hardening_primary_reason")),
        "lifecycle_same_failure_signature_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("same_failure_signature")),
        "lifecycle_same_failure_bucket_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("same_failure_bucket")),
        "lifecycle_same_failure_persistence_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("same_failure_persistence")),
        "lifecycle_no_progress_status_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("no_progress_status")),
        "lifecycle_oscillation_status_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("oscillation_status")),
        "lifecycle_retry_freeze_status_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("retry_freeze_status")),
        "lifecycle_hardening_stop_required_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("hardening_stop_required")),
        "lifecycle_lane_stabilization_contract_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "lane_stabilization_contract_present"
            )
        ),
        "lifecycle_observability_rollup_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "observability_rollup_present"
            )
        ),
        "lifecycle_failure_bucketing_hardening_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "failure_bucketing_hardening_present"
            )
        ),
        "lifecycle_artifact_retention_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "artifact_retention_present"
            )
        ),
        "lifecycle_fleet_safety_control_present: "
        + _fmt(
            output["lifecycle_artifacts"]["run_state"].get(
                "fleet_safety_control_present"
            )
        ),
        "lifecycle_lane_status: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_status")),
        "lifecycle_lane_decision: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_decision")),
        "lifecycle_lane_validity: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_validity")),
        "lifecycle_lane_confidence: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_confidence")),
        "lifecycle_current_lane_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("current_lane")),
        "lifecycle_target_lane_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("target_lane")),
        "lifecycle_lane_transition_status_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_transition_status")),
        "lifecycle_lane_transition_decision_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_transition_decision")),
        "lifecycle_lane_retry_policy_class_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_retry_policy_class")),
        "lifecycle_lane_verification_policy_class_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_verification_policy_class")),
        "lifecycle_lane_escalation_policy_class_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_escalation_policy_class")),
        "lifecycle_lane_primary_reason_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_primary_reason")),
        "lifecycle_lane_execution_allowed_overlay: "
        + _fmt(output["lifecycle_artifacts"]["run_state"].get("lane_execution_allowed")),
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
        "lifecycle_objective_contract_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("objective_status")),
        "lifecycle_objective_contract_source_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("objective_source_status")),
        "lifecycle_objective_acceptance_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("acceptance_status")),
        "lifecycle_objective_scope_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("scope_status")),
        "lifecycle_objective_required_artifacts_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("required_artifacts_status")),
        "lifecycle_objective_acceptance_criteria_total: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("acceptance_criteria_total")),
        "lifecycle_objective_acceptance_criteria_defined: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("acceptance_criteria_defined")),
        "lifecycle_objective_required_artifacts_total: "
        + _fmt(output["lifecycle_artifacts"]["objective_contract"].get("required_artifacts_total")),
        "lifecycle_completion_contract_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("completion_status")),
        "lifecycle_completion_done_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("done_status")),
        "lifecycle_completion_safe_closure_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("safe_closure_status")),
        "lifecycle_completion_evidence_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("completion_evidence_status")),
        "lifecycle_completion_closure_decision_artifact: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("closure_decision")),
        "lifecycle_completion_lifecycle_alignment_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("lifecycle_alignment_status")),
        "lifecycle_completion_required_evidence_total: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("required_evidence_total")),
        "lifecycle_completion_missing_evidence_total: "
        + _fmt(output["lifecycle_artifacts"]["completion_contract"].get("missing_evidence_total")),
        "lifecycle_approval_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["approval_transport"].get("approval_status")),
        "lifecycle_approval_decision_artifact: "
        + _fmt(output["lifecycle_artifacts"]["approval_transport"].get("approval_decision")),
        "lifecycle_approval_scope_artifact: "
        + _fmt(output["lifecycle_artifacts"]["approval_transport"].get("approval_scope")),
        "lifecycle_approval_transport_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["approval_transport"].get("approval_transport_status")),
        "lifecycle_approval_compatibility_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["approval_transport"].get("approval_compatibility_status")),
        "lifecycle_approval_blocked_reason_artifact: "
        + _fmt(output["lifecycle_artifacts"]["approval_transport"].get("approval_blocked_reason")),
        "lifecycle_reconcile_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["reconcile_contract"].get("reconcile_status")),
        "lifecycle_reconcile_decision_artifact: "
        + _fmt(output["lifecycle_artifacts"]["reconcile_contract"].get("reconcile_decision")),
        "lifecycle_reconcile_alignment_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["reconcile_contract"].get("reconcile_alignment_status")),
        "lifecycle_reconcile_primary_mismatch_artifact: "
        + _fmt(output["lifecycle_artifacts"]["reconcile_contract"].get("reconcile_primary_mismatch")),
        "lifecycle_reconcile_transport_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["reconcile_contract"].get("reconcile_transport_status")),
        "lifecycle_repair_suggestion_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_suggestion_contract"].get("repair_suggestion_status")),
        "lifecycle_repair_suggestion_decision_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_suggestion_contract"].get("repair_suggestion_decision")),
        "lifecycle_repair_suggestion_class_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_suggestion_contract"].get("repair_suggestion_class")),
        "lifecycle_repair_suggestion_priority_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_suggestion_contract"].get("repair_suggestion_priority")),
        "lifecycle_repair_primary_reason_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_suggestion_contract"].get("repair_primary_reason")),
        "lifecycle_repair_plan_status_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_plan_transport"].get("repair_plan_status")),
        "lifecycle_repair_plan_decision_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_plan_transport"].get("repair_plan_decision")),
        "lifecycle_repair_plan_class_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_plan_transport"].get("repair_plan_class")),
        "lifecycle_repair_plan_priority_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_plan_transport"].get("repair_plan_priority")),
        "lifecycle_repair_plan_primary_reason_artifact: "
        + _fmt(output["lifecycle_artifacts"]["repair_plan_transport"].get("repair_plan_primary_reason")),
        "lifecycle_repair_approval_binding_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["repair_approval_binding"].get(
                "repair_approval_binding_status"
            )
        ),
        "lifecycle_repair_approval_binding_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["repair_approval_binding"].get(
                "repair_approval_binding_decision"
            )
        ),
        "lifecycle_repair_approval_binding_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["repair_approval_binding"].get(
                "repair_approval_binding_validity"
            )
        ),
        "lifecycle_repair_approval_binding_compatibility_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["repair_approval_binding"].get(
                "repair_approval_binding_compatibility_status"
            )
        ),
        "lifecycle_repair_approval_binding_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["repair_approval_binding"].get(
                "repair_approval_binding_primary_reason"
            )
        ),
        "lifecycle_execution_authorization_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_authorization_gate"].get(
                "execution_authorization_status"
            )
        ),
        "lifecycle_execution_authorization_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_authorization_gate"].get(
                "execution_authorization_decision"
            )
        ),
        "lifecycle_execution_authorization_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_authorization_gate"].get(
                "execution_authorization_validity"
            )
        ),
        "lifecycle_execution_authorization_confidence_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_authorization_gate"].get(
                "execution_authorization_confidence"
            )
        ),
        "lifecycle_execution_authorization_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_authorization_gate"].get(
                "execution_authorization_primary_reason"
            )
        ),
        "lifecycle_bounded_execution_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["bounded_execution_bridge"].get(
                "bounded_execution_status"
            )
        ),
        "lifecycle_bounded_execution_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["bounded_execution_bridge"].get(
                "bounded_execution_decision"
            )
        ),
        "lifecycle_bounded_execution_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["bounded_execution_bridge"].get(
                "bounded_execution_validity"
            )
        ),
        "lifecycle_bounded_execution_confidence_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["bounded_execution_bridge"].get(
                "bounded_execution_confidence"
            )
        ),
        "lifecycle_bounded_execution_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["bounded_execution_bridge"].get(
                "bounded_execution_primary_reason"
            )
        ),
        "lifecycle_execution_result_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_result_contract"].get(
                "execution_result_status"
            )
        ),
        "lifecycle_execution_result_outcome_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_result_contract"].get(
                "execution_result_outcome"
            )
        ),
        "lifecycle_execution_result_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_result_contract"].get(
                "execution_result_validity"
            )
        ),
        "lifecycle_execution_result_confidence_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_result_contract"].get(
                "execution_result_confidence"
            )
        ),
        "lifecycle_execution_result_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["execution_result_contract"].get(
                "execution_result_primary_reason"
            )
        ),
        "lifecycle_verification_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "verification_status"
            )
        ),
        "lifecycle_verification_outcome_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "verification_outcome"
            )
        ),
        "lifecycle_verification_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "verification_validity"
            )
        ),
        "lifecycle_verification_confidence_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "verification_confidence"
            )
        ),
        "lifecycle_verification_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "verification_primary_reason"
            )
        ),
        "lifecycle_closure_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "closure_status"
            )
        ),
        "lifecycle_closure_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["verification_closure_contract"].get(
                "closure_decision"
            )
        ),
        "lifecycle_retry_loop_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["retry_reentry_loop_contract"].get(
                "retry_loop_status"
            )
        ),
        "lifecycle_retry_loop_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["retry_reentry_loop_contract"].get(
                "retry_loop_decision"
            )
        ),
        "lifecycle_retry_loop_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["retry_reentry_loop_contract"].get(
                "retry_loop_validity"
            )
        ),
        "lifecycle_retry_loop_confidence_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["retry_reentry_loop_contract"].get(
                "retry_loop_confidence"
            )
        ),
        "lifecycle_retry_loop_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["retry_reentry_loop_contract"].get(
                "loop_primary_reason"
            )
        ),
        "lifecycle_endgame_closure_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["endgame_closure_contract"].get(
                "endgame_closure_status"
            )
        ),
        "lifecycle_endgame_closure_outcome_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["endgame_closure_contract"].get(
                "endgame_closure_outcome"
            )
        ),
        "lifecycle_final_closure_class_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["endgame_closure_contract"].get(
                "final_closure_class"
            )
        ),
        "lifecycle_terminal_stop_class_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["endgame_closure_contract"].get(
                "terminal_stop_class"
            )
        ),
        "lifecycle_endgame_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["endgame_closure_contract"].get(
                "endgame_primary_reason"
            )
        ),
        "lifecycle_loop_hardening_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["loop_hardening_contract"].get(
                "loop_hardening_status"
            )
        ),
        "lifecycle_loop_hardening_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["loop_hardening_contract"].get(
                "loop_hardening_decision"
            )
        ),
        "lifecycle_loop_hardening_validity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["loop_hardening_contract"].get(
                "loop_hardening_validity"
            )
        ),
        "lifecycle_loop_hardening_confidence_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["loop_hardening_contract"].get(
                "loop_hardening_confidence"
            )
        ),
        "lifecycle_loop_hardening_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["loop_hardening_contract"].get(
                "loop_hardening_primary_reason"
            )
        ),
        "lifecycle_lane_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["lane_stabilization_contract"].get(
                "lane_status"
            )
        ),
        "lifecycle_lane_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["lane_stabilization_contract"].get(
                "lane_decision"
            )
        ),
        "lifecycle_current_lane_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["lane_stabilization_contract"].get(
                "current_lane"
            )
        ),
        "lifecycle_target_lane_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["lane_stabilization_contract"].get(
                "target_lane"
            )
        ),
        "lifecycle_lane_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["lane_stabilization_contract"].get(
                "lane_primary_reason"
            )
        ),
        "lifecycle_observability_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["observability_rollup_contract"].get(
                "observability_status"
            )
        ),
        "lifecycle_observability_terminal_class_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["observability_rollup_contract"].get(
                "run_terminal_class"
            )
        ),
        "lifecycle_observability_lane_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["observability_rollup_contract"].get(
                "lane"
            )
        ),
        "lifecycle_observability_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["observability_rollup_contract"].get(
                "observability_primary_reason"
            )
        ),
        "lifecycle_failure_bucket_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucket_rollup"].get(
                "failure_bucket_status"
            )
        ),
        "lifecycle_primary_failure_bucket_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucket_rollup"].get(
                "primary_failure_bucket"
            )
        ),
        "lifecycle_failure_bucket_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucket_rollup"].get(
                "failure_bucket_primary_reason"
            )
        ),
        "lifecycle_fleet_terminal_class_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_run_rollup"].get(
                "fleet_terminal_class"
            )
        ),
        "lifecycle_fleet_primary_failure_bucket_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_run_rollup"].get(
                "fleet_primary_failure_bucket"
            )
        ),
        "lifecycle_fleet_observability_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_run_rollup"].get(
                "fleet_observability_status"
            )
        ),
        "lifecycle_fleet_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_run_rollup"].get(
                "fleet_primary_reason"
            )
        ),
        "lifecycle_hardened_primary_failure_bucket_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucketing_hardening_contract"].get(
                "primary_failure_bucket"
            )
        ),
        "lifecycle_hardened_bucket_family_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucketing_hardening_contract"].get(
                "bucket_family"
            )
        ),
        "lifecycle_hardened_bucket_severity_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucketing_hardening_contract"].get(
                "bucket_severity"
            )
        ),
        "lifecycle_hardened_bucket_stability_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucketing_hardening_contract"].get(
                "bucket_stability_class"
            )
        ),
        "lifecycle_hardened_bucket_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["failure_bucketing_hardening_contract"].get(
                "failure_bucketing_primary_reason"
            )
        ),
        "lifecycle_artifact_retention_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["artifact_retention_contract"].get(
                "artifact_retention_status"
            )
        ),
        "lifecycle_retention_policy_class_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["artifact_retention_contract"].get(
                "retention_policy_class"
            )
        ),
        "lifecycle_retention_compaction_class_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["artifact_retention_contract"].get(
                "retention_compaction_class"
            )
        ),
        "lifecycle_retention_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["artifact_retention_contract"].get(
                "retention_primary_reason"
            )
        ),
        "lifecycle_fleet_safety_status_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_safety_control_contract"].get(
                "fleet_safety_status"
            )
        ),
        "lifecycle_fleet_safety_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_safety_control_contract"].get(
                "fleet_safety_decision"
            )
        ),
        "lifecycle_fleet_restart_decision_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_safety_control_contract"].get(
                "fleet_restart_decision"
            )
        ),
        "lifecycle_fleet_safety_scope_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_safety_control_contract"].get(
                "fleet_safety_scope"
            )
        ),
        "lifecycle_fleet_safety_primary_reason_artifact: "
        + _fmt(
            output["lifecycle_artifacts"]["fleet_safety_control_contract"].get(
                "fleet_safety_primary_reason"
            )
        ),
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
        f"lifecycle_objective_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('objective_contract'))}",
        f"lifecycle_completion_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('completion_contract'))}",
        f"lifecycle_approval_transport_path: {_fmt(output['lifecycle_artifacts']['paths'].get('approval_transport'))}",
        f"lifecycle_reconcile_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('reconcile_contract'))}",
        f"lifecycle_repair_suggestion_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('repair_suggestion_contract'))}",
        f"lifecycle_repair_plan_transport_path: {_fmt(output['lifecycle_artifacts']['paths'].get('repair_plan_transport'))}",
        f"lifecycle_repair_approval_binding_path: {_fmt(output['lifecycle_artifacts']['paths'].get('repair_approval_binding'))}",
        f"lifecycle_execution_authorization_gate_path: {_fmt(output['lifecycle_artifacts']['paths'].get('execution_authorization_gate'))}",
        f"lifecycle_bounded_execution_bridge_path: {_fmt(output['lifecycle_artifacts']['paths'].get('bounded_execution_bridge'))}",
        f"lifecycle_execution_result_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('execution_result_contract'))}",
        f"lifecycle_verification_closure_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('verification_closure_contract'))}",
        f"lifecycle_retry_reentry_loop_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('retry_reentry_loop_contract'))}",
        f"lifecycle_endgame_closure_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('endgame_closure_contract'))}",
        f"lifecycle_loop_hardening_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('loop_hardening_contract'))}",
        f"lifecycle_lane_stabilization_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('lane_stabilization_contract'))}",
        f"lifecycle_observability_rollup_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('observability_rollup_contract'))}",
        f"lifecycle_failure_bucket_rollup_path: {_fmt(output['lifecycle_artifacts']['paths'].get('failure_bucket_rollup'))}",
        f"lifecycle_fleet_run_rollup_path: {_fmt(output['lifecycle_artifacts']['paths'].get('fleet_run_rollup'))}",
        f"lifecycle_failure_bucketing_hardening_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('failure_bucketing_hardening_contract'))}",
        f"lifecycle_retention_manifest_path: {_fmt(output['lifecycle_artifacts']['paths'].get('retention_manifest'))}",
        f"lifecycle_artifact_retention_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('artifact_retention_contract'))}",
        f"lifecycle_fleet_safety_control_contract_path: {_fmt(output['lifecycle_artifacts']['paths'].get('fleet_safety_control_contract'))}",
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

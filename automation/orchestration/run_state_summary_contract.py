from __future__ import annotations

from typing import Any
from typing import Mapping

from automation.orchestration.approval_transport import APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.approval_transport import build_approval_run_state_summary_surface
from automation.orchestration.completion_contract import COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.completion_contract import build_completion_run_state_summary_surface
from automation.orchestration.execution_authorization_gate import (
    EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.execution_authorization_gate import (
    build_execution_authorization_gate_run_state_summary_surface,
)
from automation.orchestration.execution_result_contract import (
    EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.execution_result_contract import (
    build_execution_result_contract_run_state_summary_surface,
)
from automation.orchestration.verification_closure_contract import (
    VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.verification_closure_contract import (
    build_verification_closure_run_state_summary_surface,
)
from automation.orchestration.retry_reentry_loop_contract import (
    RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.retry_reentry_loop_contract import (
    build_retry_reentry_loop_run_state_summary_surface,
)
from automation.orchestration.endgame_closure_contract import (
    ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.endgame_closure_contract import (
    build_endgame_closure_run_state_summary_surface,
)
from automation.orchestration.loop_hardening_contract import (
    LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.loop_hardening_contract import (
    build_loop_hardening_run_state_summary_surface,
)
from automation.orchestration.lane_stabilization_contract import (
    LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.lane_stabilization_contract import (
    build_lane_stabilization_run_state_summary_surface,
)
from automation.orchestration.observability_rollup import (
    OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.observability_rollup import (
    build_observability_rollup_run_state_summary_surface,
)
from automation.orchestration.failure_bucketing_hardening import (
    FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.failure_bucketing_hardening import (
    build_failure_bucketing_hardening_run_state_summary_surface,
)
from automation.orchestration.artifact_retention import (
    ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.artifact_retention import (
    build_artifact_retention_run_state_summary_surface,
)
from automation.orchestration.fleet_safety_control import (
    FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.fleet_safety_control import (
    build_fleet_safety_control_run_state_summary_surface,
)
from automation.orchestration.approval_email_delivery import (
    APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_email_delivery import (
    build_approval_email_delivery_run_state_summary_surface,
)
from automation.orchestration.approval_runtime_policy import (
    APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_runtime_policy import (
    build_approval_runtime_rules_run_state_summary_surface,
)
from automation.orchestration.approval_delivery_adapter import (
    APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_delivery_adapter import (
    build_approval_delivery_handoff_run_state_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    APPROVAL_RESPONSE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_response_ingest import (
    APPROVED_RESTART_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_response_ingest import (
    build_approval_response_run_state_summary_surface,
)
from automation.orchestration.approval_response_ingest import (
    build_approved_restart_run_state_summary_surface,
)
from automation.orchestration.approval_safety import (
    APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.approval_safety import (
    build_approval_safety_run_state_summary_surface,
)
from automation.orchestration.bounded_execution_bridge import (
    BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.bounded_execution_bridge import (
    build_bounded_execution_bridge_run_state_summary_surface,
)
from automation.orchestration.lifecycle_terminal_state import LIFECYCLE_SUMMARY_SAFE_FIELDS
from automation.orchestration.objective_contract import OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.objective_contract import build_objective_run_state_summary_surface
from automation.orchestration.operator_explainability import OPERATOR_RENDERING_ONLY_FIELDS
from automation.orchestration.operator_explainability import OPERATOR_SUMMARY_SAFE_FIELDS
from automation.orchestration.repair_suggestion_contract import REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.repair_suggestion_contract import build_repair_suggestion_run_state_summary_surface
from automation.orchestration.repair_approval_binding import (
    REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS,
)
from automation.orchestration.repair_approval_binding import (
    build_repair_approval_binding_run_state_summary_surface,
)
from automation.orchestration.repair_plan_transport import REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.repair_plan_transport import build_repair_plan_transport_run_state_summary_surface
from automation.orchestration.reconcile_contract import RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS
from automation.orchestration.reconcile_contract import build_reconcile_run_state_summary_surface
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface
from automation.orchestration.operator_explainability import build_operator_explainability_surface

CANONICAL_RUN_STATE_TRUTH_SURFACES = (
    "loop_state",
    "authority_validation",
    "remote_github",
    "rollback_aftermath",
    "policy",
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
    "failure_bucketing_hardening_contract",
    "artifact_retention_contract",
    "fleet_safety_control_contract",
    "approval_email_delivery_contract",
    "approval_runtime_rules_contract",
    "approval_delivery_handoff_contract",
    "approval_response_contract",
    "approved_restart_contract",
    "approval_safety_contract",
    "lifecycle_contract",
    "orchestration",
)

MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "state",
    "orchestration_state",
    "summary",
    "units_total",
    "units_completed",
    "units_blocked",
    "units_failed",
    "units_pending",
    "global_stop",
    "continue_allowed",
    "run_paused",
    "manual_intervention_required",
    "rollback_evaluation_pending",
    "global_stop_recommended",
    "next_run_action",
    "loop_state",
    "next_safe_action",
    "loop_blocked_reason",
    "resumable",
    "terminal",
    "policy_status",
    "policy_blocked",
    "policy_manual_required",
    "policy_replan_required",
    "policy_resume_allowed",
    "policy_terminal",
    "policy_primary_blocker_class",
    "policy_primary_action",
    *OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVAL_RESPONSE_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVED_RESTART_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS,
    *LIFECYCLE_SUMMARY_SAFE_FIELDS,
    *OPERATOR_SUMMARY_SAFE_FIELDS,
)
MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS = tuple(
    dict.fromkeys(MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS)
)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return max(0, int(stripped))
    return 0


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return False


def is_manifest_summary_safe_field(field_name: str) -> bool:
    return field_name in MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS


def select_manifest_run_state_summary_compact(
    run_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(run_state_payload or {})
    objective_surface = build_objective_run_state_summary_surface(payload)
    lifecycle_surface = build_lifecycle_terminal_state_surface({**payload, **objective_surface})
    completion_surface = build_completion_run_state_summary_surface(
        {**payload, **objective_surface, **lifecycle_surface}
    )
    approval_surface = build_approval_run_state_summary_surface(
        {**payload, **objective_surface, **lifecycle_surface, **completion_surface}
    )
    reconcile_surface = build_reconcile_run_state_summary_surface(
        {**payload, **objective_surface, **lifecycle_surface, **completion_surface, **approval_surface}
    )
    repair_surface = build_repair_suggestion_run_state_summary_surface(
        {
            **payload,
            **objective_surface,
            **lifecycle_surface,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
        }
    )
    repair_plan_surface = build_repair_plan_transport_run_state_summary_surface(
        {
            **payload,
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
            **payload,
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
            **payload,
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
            **payload,
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
            **payload,
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
            **payload,
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
            **payload,
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
    endgame_closure_surface = build_endgame_closure_run_state_summary_surface(
        {
            **payload,
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
            **payload,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
            **endgame_closure_surface,
        }
    )
    lane_stabilization_surface = build_lane_stabilization_run_state_summary_surface(
        {
            **payload,
            **completion_surface,
            **approval_surface,
            **reconcile_surface,
            **execution_authorization_surface,
            **bounded_execution_surface,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
            **endgame_closure_surface,
            **loop_hardening_surface,
        }
    )
    observability_surface = build_observability_rollup_run_state_summary_surface(
        {
            **payload,
            **execution_result_surface,
            **verification_closure_surface,
            **retry_reentry_surface,
            **endgame_closure_surface,
            **loop_hardening_surface,
            **lane_stabilization_surface,
        }
    )
    failure_bucketing_hardening_surface = (
        build_failure_bucketing_hardening_run_state_summary_surface(
            {
                **payload,
                **loop_hardening_surface,
                **observability_surface,
            }
        )
    )
    artifact_retention_surface = build_artifact_retention_run_state_summary_surface(
        {
            **payload,
            **failure_bucketing_hardening_surface,
        }
    )
    fleet_safety_control_surface = build_fleet_safety_control_run_state_summary_surface(
        {
            **payload,
            **failure_bucketing_hardening_surface,
            **artifact_retention_surface,
        }
    )
    approval_email_delivery_surface = (
        build_approval_email_delivery_run_state_summary_surface(
            {
                **payload,
                **fleet_safety_control_surface,
            }
        )
    )
    approval_runtime_rules_surface = build_approval_runtime_rules_run_state_summary_surface(
        payload
    )
    approval_delivery_handoff_surface = build_approval_delivery_handoff_run_state_summary_surface(
        payload
    )
    approval_response_surface = build_approval_response_run_state_summary_surface(
        payload
    )
    approved_restart_surface = build_approved_restart_run_state_summary_surface(
        payload
    )
    approval_safety_surface = build_approval_safety_run_state_summary_surface(
        payload
    )
    operator_surface = build_operator_explainability_surface(
        {
            **payload,
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
            **endgame_closure_surface,
            **loop_hardening_surface,
            **lane_stabilization_surface,
            **observability_surface,
            **failure_bucketing_hardening_surface,
            **artifact_retention_surface,
            **fleet_safety_control_surface,
            **approval_email_delivery_surface,
            **approval_runtime_rules_surface,
            **approval_delivery_handoff_surface,
            **approval_response_surface,
            **approved_restart_surface,
            **approval_safety_surface,
        },
        include_rendering_details=False,
    )
    merged = {
        **payload,
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
        **endgame_closure_surface,
        **loop_hardening_surface,
        **lane_stabilization_surface,
        **observability_surface,
        **failure_bucketing_hardening_surface,
        **artifact_retention_surface,
        **fleet_safety_control_surface,
        **approval_email_delivery_surface,
        **approval_runtime_rules_surface,
        **approval_delivery_handoff_surface,
        **approval_response_surface,
        **approved_restart_surface,
        **approval_safety_surface,
        **operator_surface,
    }

    int_fields = {
        "units_total",
        "units_completed",
        "units_blocked",
        "units_failed",
        "units_pending",
        "attempt_count",
        "max_attempt_count",
        "reentry_count",
        "max_reentry_count",
        "same_failure_count",
        "max_same_failure_count",
        "lane_attempt_budget",
        "lane_reentry_budget",
        "lane_transition_count",
        "max_lane_transition_count",
    }
    bool_fields = {
        "global_stop",
        "continue_allowed",
        "run_paused",
        "manual_intervention_required",
        "rollback_evaluation_pending",
        "global_stop_recommended",
        "resumable",
        "terminal",
        "policy_blocked",
        "policy_manual_required",
        "policy_replan_required",
        "policy_resume_allowed",
        "policy_terminal",
        "objective_contract_present",
        "completion_contract_present",
        "completion_manual_required",
        "completion_replan_required",
        "approval_transport_present",
        "approval_required",
        "reconcile_contract_present",
        "reconcile_waiting_on_truth",
        "reconcile_manual_required",
        "reconcile_replan_required",
        "repair_suggestion_contract_present",
        "repair_manual_required",
        "repair_replan_required",
        "repair_truth_gathering_required",
        "repair_plan_transport_present",
        "repair_plan_manual_required",
        "repair_plan_replan_required",
        "repair_plan_truth_gathering_required",
        "repair_approval_binding_present",
        "repair_approval_binding_manual_required",
        "repair_approval_binding_replan_required",
        "repair_approval_binding_truth_gathering_required",
        "execution_authorization_gate_present",
        "execution_authorization_manual_required",
        "execution_authorization_replan_required",
        "execution_authorization_truth_gathering_required",
        "bounded_execution_bridge_present",
        "bounded_execution_manual_required",
        "bounded_execution_replan_required",
        "bounded_execution_truth_gathering_required",
        "execution_result_contract_present",
        "execution_result_attempted",
        "execution_result_receipt_present",
        "execution_result_output_present",
        "execution_result_manual_followup_required",
        "verification_closure_contract_present",
        "objective_satisfied",
        "completion_satisfied",
        "safely_closable",
        "manual_closure_required",
        "closure_followup_required",
        "external_truth_required",
        "retry_reentry_loop_contract_present",
        "retry_allowed",
        "reentry_allowed",
        "retry_exhausted",
        "reentry_exhausted",
        "same_failure_exhausted",
        "terminal_stop_required",
        "manual_escalation_required",
        "replan_required",
        "recollect_required",
        "same_lane_retry_allowed",
        "repair_retry_allowed",
        "no_progress_stop_required",
        "endgame_closure_contract_present",
        "safely_closed",
        "completed_but_not_closed",
        "rollback_complete_but_not_closed",
        "manual_closure_only",
        "external_truth_pending",
        "closure_unresolved",
        "terminal_success",
        "terminal_non_success",
        "operator_followup_required",
        "further_retry_allowed",
        "further_reentry_allowed",
        "loop_hardening_contract_present",
        "same_failure_detected",
        "same_failure_stop_required",
        "no_progress_detected",
        "no_progress_stop_required",
        "oscillation_detected",
        "unstable_loop_detected",
        "retry_freeze_required",
        "cool_down_required",
        "forced_manual_escalation_required",
        "hardening_stop_required",
        "lane_stabilization_contract_present",
        "lane_valid",
        "lane_mismatch_detected",
        "lane_transition_required",
        "lane_transition_allowed",
        "lane_transition_blocked",
        "lane_stop_required",
        "lane_manual_review_required",
        "lane_replan_required",
        "lane_truth_gathering_required",
        "lane_execution_allowed",
        "observability_rollup_present",
        "failure_bucketing_hardening_present",
        "artifact_retention_present",
        "fleet_safety_control_present",
        "approval_email_delivery_present",
        "approval_runtime_rules_present",
        "approval_delivery_handoff_present",
        "approval_response_present",
        "approved_restart_present",
        "approval_safety_present",
        "lifecycle_safely_closed",
        "lifecycle_terminal",
        "lifecycle_resumable",
        "lifecycle_manual_required",
        "lifecycle_replan_required",
        "lifecycle_execution_complete_not_closed",
        "lifecycle_rollback_complete_not_closed",
    }

    summary: dict[str, Any] = {}
    for field in MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS:
        value = merged.get(field)
        if field in int_fields:
            summary[field] = _normalize_non_negative_int(value)
        elif field in bool_fields:
            summary[field] = _normalize_bool(value)
        else:
            summary[field] = _normalize_text(value)
    _apply_compact_stabilization(summary)
    return summary


def _apply_compact_stabilization(summary: dict[str, Any]) -> None:
    retry_status = _normalize_text(summary.get("retry_loop_status"))
    retry_decision = _normalize_text(summary.get("retry_loop_decision"))
    terminal_stop_required = _normalize_bool(summary.get("terminal_stop_required"))

    if retry_status in {"stop_required", "exhausted", "not_applicable", "insufficient_truth"}:
        summary["retry_allowed"] = False
        summary["reentry_allowed"] = False

    if retry_decision == "same_lane_retry":
        summary["same_lane_retry_allowed"] = True
        summary["retry_allowed"] = True
    if retry_decision == "repair_retry":
        summary["repair_retry_allowed"] = True
        summary["retry_allowed"] = True
    if retry_decision == "recollect":
        summary["recollect_required"] = True
        summary["reentry_allowed"] = True
    if retry_decision == "replan":
        summary["replan_required"] = True
        summary["reentry_allowed"] = True
    if retry_decision == "escalate_manual":
        summary["manual_escalation_required"] = True
        terminal_stop_required = True

    if terminal_stop_required:
        summary["terminal_stop_required"] = True
        summary["retry_allowed"] = False
        summary["reentry_allowed"] = False

    endgame_status = _normalize_text(summary.get("endgame_closure_status"))
    final_class = _normalize_text(summary.get("final_closure_class"))
    terminal_class = _normalize_text(summary.get("terminal_stop_class"))

    safely_closed = endgame_status == "safely_closed" or final_class == "safely_closed"
    if safely_closed:
        summary["endgame_closure_status"] = "safely_closed"
        summary["endgame_closure_outcome"] = "terminal_success_closed"
        summary["final_closure_class"] = "safely_closed"
        summary["terminal_stop_class"] = "terminal_success"
        summary["closure_resolution_status"] = "resolved"
        summary["safely_closed"] = True
        summary["terminal_success"] = True
        summary["terminal_non_success"] = False
        summary["operator_followup_required"] = False
        summary["further_retry_allowed"] = False
        summary["further_reentry_allowed"] = False

    class_to_flag = {
        "completed_but_not_closed": "completed_but_not_closed",
        "rollback_complete_but_not_closed": "rollback_complete_but_not_closed",
        "manual_closure_only": "manual_closure_only",
        "external_truth_pending": "external_truth_pending",
        "closure_unresolved": "closure_unresolved",
    }
    for closure_class, flag_field in class_to_flag.items():
        summary[flag_field] = final_class == closure_class

    if summary.get("safely_closed"):
        summary["completed_but_not_closed"] = False
        summary["rollback_complete_but_not_closed"] = False
        summary["manual_closure_only"] = False
        summary["external_truth_pending"] = False
        summary["closure_unresolved"] = False

    if terminal_class == "terminal_success":
        summary["terminal_success"] = True
        summary["terminal_non_success"] = False
    elif terminal_class in {
        "terminal_non_success",
        "manual_terminal",
        "closure_unresolved_terminal",
    }:
        summary["terminal_success"] = False
        summary["terminal_non_success"] = True

    summary["further_retry_allowed"] = _normalize_bool(
        summary.get("further_retry_allowed")
    ) and _normalize_bool(summary.get("retry_allowed"))
    summary["further_reentry_allowed"] = _normalize_bool(
        summary.get("further_reentry_allowed")
    ) and _normalize_bool(summary.get("reentry_allowed"))

    if _normalize_bool(summary.get("terminal_stop_required")) and retry_decision in {
        "stop_terminal",
        "escalate_manual",
    }:
        summary["further_retry_allowed"] = False
        summary["further_reentry_allowed"] = False

    hardening_status = _normalize_text(summary.get("loop_hardening_status"))
    hardening_decision = _normalize_text(summary.get("loop_hardening_decision"))
    if hardening_status == "stable":
        summary["retry_freeze_required"] = False
        summary["hardening_stop_required"] = False
    if hardening_status == "freeze":
        summary["retry_freeze_required"] = True
    if hardening_status == "stop_required":
        summary["hardening_stop_required"] = True
    if hardening_decision == "freeze_retry":
        summary["retry_freeze_required"] = True
    if hardening_decision == "cool_down":
        summary["cool_down_required"] = True
    if hardening_decision == "escalate_manual":
        summary["forced_manual_escalation_required"] = True
    if hardening_decision == "stop_terminal":
        summary["hardening_stop_required"] = True
    if _normalize_bool(summary.get("no_progress_stop_required")):
        summary["no_progress_detected"] = True
        summary["hardening_stop_required"] = True
    summary["unstable_loop_detected"] = _normalize_bool(
        summary.get("unstable_loop_detected")
    ) or _normalize_bool(summary.get("oscillation_detected")) or _normalize_bool(
        summary.get("no_progress_detected")
    )
    if _normalize_bool(summary.get("hardening_stop_required")):
        summary["further_retry_allowed"] = False
        summary["further_reentry_allowed"] = False

    lane_status = _normalize_text(summary.get("lane_status"))
    lane_decision = _normalize_text(summary.get("lane_decision"))
    lane_preconditions = _normalize_text(summary.get("lane_preconditions_status"))

    if lane_status == "lane_valid":
        summary["lane_valid"] = True
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = False
    elif lane_status == "lane_mismatch":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = True
        summary["lane_transition_required"] = True
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = False
    elif lane_status == "lane_transition_blocked":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_required"] = True
        summary["lane_transition_blocked"] = True
        summary["lane_stop_required"] = False
    elif lane_status == "lane_stop_required":
        summary["lane_valid"] = False
        summary["lane_mismatch_detected"] = False
        summary["lane_transition_blocked"] = False
        summary["lane_stop_required"] = True
    elif lane_status in {"not_applicable", "insufficient_truth"}:
        summary["lane_valid"] = False
        summary["lane_execution_allowed"] = False

    if lane_decision == "transition_lane":
        summary["lane_transition_required"] = True
    if _normalize_bool(summary.get("lane_transition_required")) and lane_decision not in {
        "transition_lane",
        "not_applicable",
    }:
        summary["lane_decision"] = "transition_lane"

    if _normalize_text(summary.get("lane_transition_status")) == "ready":
        summary["lane_transition_required"] = True
        summary["lane_transition_allowed"] = True
    if _normalize_text(summary.get("lane_transition_status")) == "blocked":
        summary["lane_transition_required"] = True
        summary["lane_transition_blocked"] = True

    if lane_preconditions != "satisfied":
        summary["lane_execution_allowed"] = False
    if _normalize_bool(summary.get("lane_mismatch_detected")):
        summary["lane_execution_allowed"] = False
    if hardening_status in {"freeze", "stop_required"} or _normalize_bool(
        summary.get("hardening_stop_required")
    ):
        summary["lane_execution_allowed"] = False


def build_manifest_run_state_summary_contract_surface() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "canonical_run_truth_owner": "run_state.json",
        "manifest_summary_policy": "lightweight_summary_and_references_only",
        "canonical_run_truth_surfaces": list(CANONICAL_RUN_STATE_TRUTH_SURFACES),
        "summary_safe_fields": list(MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "objective_summary_safe_fields": list(OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "completion_summary_safe_fields": list(COMPLETION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "approval_summary_safe_fields": list(APPROVAL_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "reconcile_summary_safe_fields": list(RECONCILE_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "repair_suggestion_summary_safe_fields": list(REPAIR_SUGGESTION_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "repair_plan_transport_summary_safe_fields": list(
            REPAIR_PLAN_TRANSPORT_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "repair_approval_binding_summary_safe_fields": list(
            REPAIR_APPROVAL_BINDING_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "execution_authorization_summary_safe_fields": list(
            EXECUTION_AUTHORIZATION_GATE_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "bounded_execution_summary_safe_fields": list(
            BOUNDED_EXECUTION_BRIDGE_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "execution_result_summary_safe_fields": list(
            EXECUTION_RESULT_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "verification_closure_summary_safe_fields": list(
            VERIFICATION_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "retry_reentry_loop_summary_safe_fields": list(
            RETRY_REENTRY_LOOP_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "endgame_closure_summary_safe_fields": list(
            ENDGAME_CLOSURE_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "loop_hardening_summary_safe_fields": list(
            LOOP_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "lane_stabilization_summary_safe_fields": list(
            LANE_STABILIZATION_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "observability_summary_safe_fields": list(
            OBSERVABILITY_ROLLUP_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "failure_bucketing_hardening_summary_safe_fields": list(
            FAILURE_BUCKETING_HARDENING_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "artifact_retention_summary_safe_fields": list(
            ARTIFACT_RETENTION_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "fleet_safety_control_summary_safe_fields": list(
            FLEET_SAFETY_CONTROL_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "approval_email_delivery_summary_safe_fields": list(
            APPROVAL_EMAIL_DELIVERY_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "approval_runtime_rules_summary_safe_fields": list(
            APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "approval_delivery_handoff_summary_safe_fields": list(
            APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "approval_response_summary_safe_fields": list(
            APPROVAL_RESPONSE_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "approved_restart_summary_safe_fields": list(
            APPROVED_RESTART_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "approval_safety_summary_safe_fields": list(
            APPROVAL_SAFETY_RUN_STATE_SUMMARY_SAFE_FIELDS
        ),
        "lifecycle_summary_safe_fields": list(LIFECYCLE_SUMMARY_SAFE_FIELDS),
        "rendering_only_operator_fields": list(OPERATOR_RENDERING_ONLY_FIELDS),
        "compact_summary_field": "run_state_summary_compact",
        "compatibility_summary_field": "run_state_summary",
        "compatibility_summary_mode": "alias_to_compact_deprecated_verbose",
    }

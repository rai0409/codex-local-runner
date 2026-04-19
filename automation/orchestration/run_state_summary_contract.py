from __future__ import annotations

from typing import Any
from typing import Mapping

from automation.orchestration.lifecycle_terminal_state import LIFECYCLE_SUMMARY_SAFE_FIELDS
from automation.orchestration.operator_explainability import OPERATOR_RENDERING_ONLY_FIELDS
from automation.orchestration.operator_explainability import OPERATOR_SUMMARY_SAFE_FIELDS
from automation.orchestration.lifecycle_terminal_state import build_lifecycle_terminal_state_surface
from automation.orchestration.operator_explainability import build_operator_explainability_surface

CANONICAL_RUN_STATE_TRUTH_SURFACES = (
    "loop_state",
    "authority_validation",
    "remote_github",
    "rollback_aftermath",
    "policy",
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
    *LIFECYCLE_SUMMARY_SAFE_FIELDS,
    *OPERATOR_SUMMARY_SAFE_FIELDS,
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
    operator_surface = build_operator_explainability_surface(
        payload,
        include_rendering_details=False,
    )
    lifecycle_surface = build_lifecycle_terminal_state_surface(payload)
    merged = {**payload, **lifecycle_surface, **operator_surface}

    int_fields = {"units_total", "units_completed", "units_blocked", "units_failed", "units_pending"}
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
    return summary


def build_manifest_run_state_summary_contract_surface() -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "canonical_run_truth_owner": "run_state.json",
        "manifest_summary_policy": "lightweight_summary_and_references_only",
        "canonical_run_truth_surfaces": list(CANONICAL_RUN_STATE_TRUTH_SURFACES),
        "summary_safe_fields": list(MANIFEST_RUN_STATE_SUMMARY_SAFE_FIELDS),
        "lifecycle_summary_safe_fields": list(LIFECYCLE_SUMMARY_SAFE_FIELDS),
        "rendering_only_operator_fields": list(OPERATOR_RENDERING_ONLY_FIELDS),
        "compact_summary_field": "run_state_summary_compact",
        "compatibility_summary_field": "run_state_summary",
    }

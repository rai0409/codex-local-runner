from __future__ import annotations

from collections import OrderedDict
from typing import Any
from typing import Mapping


CONTRACT_ARTIFACT_ROLES = (
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
)


def _normalize_path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    return text


def build_contract_artifact_index(
    *,
    paths_by_role: Mapping[str, Any] | None,
    summaries_by_role: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    paths = dict(paths_by_role or {})
    summaries = dict(summaries_by_role or {})

    index: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
    for role in CONTRACT_ARTIFACT_ROLES:
        entry: dict[str, Any] = {}
        path_value = _normalize_path(paths.get(role))
        if path_value:
            entry["path"] = path_value

        summary_value = summaries.get(role)
        if isinstance(summary_value, Mapping):
            entry["summary"] = dict(summary_value)

        if entry:
            index[role] = entry

    return dict(index)

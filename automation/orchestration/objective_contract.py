from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

OBJECTIVE_CONTRACT_SCHEMA_VERSION = "v1"

OBJECTIVE_STATUSES = {
    "complete",
    "incomplete",
    "underspecified",
    "blocked",
}

OBJECTIVE_SOURCE_STATUSES = {
    "structured_complete",
    "structured_partial",
    "fallback_limited",
    "missing",
}

ACCEPTANCE_STATUSES = {
    "defined",
    "partially_defined",
    "undefined",
    "blocked",
}

SCOPE_STATUSES = {
    "clear",
    "partial",
    "unclear",
    "blocked",
}

REQUIRED_ARTIFACTS_STATUSES = {
    "defined",
    "partially_defined",
    "undefined",
    "blocked",
}

OBJECTIVE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "objective_contract_present",
    "objective_id",
    "objective_summary",
    "objective_type",
    "requested_outcome",
    "objective_acceptance_status",
    "objective_required_artifacts_status",
    "objective_scope_status",
    "objective_contract_status",
    "objective_contract_blocked_reason",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    seen: set[str] = set()
    items: list[str] = []
    for raw in value:
        text = _normalize_text(raw, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    if sort_items:
        return sorted(items)
    return items


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _collect_pr_plan_units(pr_plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw_units = pr_plan.get("prs")
    if not isinstance(raw_units, list):
        return []
    return [item for item in raw_units if isinstance(item, Mapping)]


def _collect_prompt_fallback_notes(units: list[Mapping[str, Any]]) -> list[str]:
    notes: list[str] = []
    for unit in units:
        markdown = _normalize_text(unit.get("codex_task_prompt_md"), default="")
        if not markdown:
            continue
        for line in markdown.splitlines():
            stripped = line.strip().lstrip("-").strip()
            if stripped:
                notes.append(stripped)
                break
        if notes:
            break
    return notes


def _priority_pick(candidates: list[tuple[int, str, str]]) -> tuple[int | None, str, str]:
    for priority, source, value in candidates:
        text = _normalize_text(value, default="")
        if text:
            return priority, source, text
    return None, "", ""


def _dedupe(items: list[str], *, sort_items: bool = False) -> list[str]:
    deduped = _normalize_string_list(items, sort_items=False)
    if sort_items:
        return sorted(deduped)
    return deduped


def _first_list_item_text(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return ""
    return _normalize_text(value[0], default="")


def _collect_scope_from_pr_plan(pr_units: list[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    in_scope: list[str] = []
    out_of_scope: list[str] = []
    for pr in pr_units:
        in_scope.extend(_normalize_string_list(pr.get("touched_files"), sort_items=True))
        out_of_scope.extend(_normalize_string_list(pr.get("forbidden_files"), sort_items=True))
    return _dedupe(in_scope, sort_items=True), _dedupe(out_of_scope, sort_items=True)


def _collect_scope_from_contracts(units: list[Mapping[str, Any]]) -> tuple[list[str], list[str]]:
    in_scope: list[str] = []
    out_of_scope: list[str] = []
    for unit in units:
        bounded = _as_mapping(unit.get("bounded_step_contract"))
        prompt = _as_mapping(unit.get("pr_implementation_prompt_contract"))
        task_scope = _as_mapping(prompt.get("task_scope"))
        in_scope.extend(_normalize_string_list(bounded.get("scope_in"), sort_items=True))
        in_scope.extend(_normalize_string_list(task_scope.get("scope_in"), sort_items=True))
        out_of_scope.extend(_normalize_string_list(bounded.get("scope_out"), sort_items=True))
        out_of_scope.extend(_normalize_string_list(task_scope.get("scope_out"), sort_items=True))
    return _dedupe(in_scope, sort_items=True), _dedupe(out_of_scope, sort_items=True)


def _collect_acceptance_from_pr_plan(
    project_brief: Mapping[str, Any],
    pr_units: list[Mapping[str, Any]],
) -> list[tuple[str, str, int, str]]:
    acceptance: list[tuple[str, str, int, str]] = []
    success_definition = _normalize_text(project_brief.get("success_definition"), default="")
    if success_definition:
        acceptance.append(("success_definition", success_definition, 1, "project_brief.success_definition"))
    for pr in pr_units:
        for text in _normalize_string_list(pr.get("acceptance_criteria"), sort_items=False):
            acceptance.append(("acceptance_criterion", text, 1, "pr_plan.prs.acceptance_criteria"))
    return acceptance


def _collect_acceptance_from_contracts(
    units: list[Mapping[str, Any]],
) -> list[tuple[str, str, int, str]]:
    acceptance: list[tuple[str, str, int, str]] = []
    for unit in units:
        bounded = _as_mapping(unit.get("bounded_step_contract"))
        prompt = _as_mapping(unit.get("pr_implementation_prompt_contract"))
        for text in _normalize_string_list(bounded.get("invariants_to_preserve"), sort_items=False):
            acceptance.append(("invariant", text, 2, "bounded_step_contract.invariants_to_preserve"))
        for text in _normalize_string_list(prompt.get("definition_of_done"), sort_items=False):
            acceptance.append(("definition_of_done", text, 2, "pr_implementation_prompt_contract.definition_of_done"))
        for text in _normalize_string_list(prompt.get("required_tests"), sort_items=False):
            acceptance.append(("required_test", text, 2, "pr_implementation_prompt_contract.required_tests"))
    return acceptance


def _normalize_acceptance_criteria(
    entries: list[tuple[str, str, int, str]],
) -> list[dict[str, Any]]:
    if not entries:
        return [
            {
                "criterion_id": "criterion_001",
                "kind": "unknown",
                "text": "",
                "source_priority": 0,
                "source": "missing",
                "status": "undefined",
            }
        ]

    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for kind, text, priority, source in entries:
        norm_text = _normalize_text(text, default="")
        key = (kind, norm_text)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "criterion_id": f"criterion_{len(normalized) + 1:03d}",
                "kind": kind,
                "text": norm_text,
                "source_priority": priority,
                "source": source,
                "status": "defined" if norm_text else "undefined",
            }
        )
    if not normalized:
        return [
            {
                "criterion_id": "criterion_001",
                "kind": "unknown",
                "text": "",
                "source_priority": 0,
                "source": "missing",
                "status": "undefined",
            }
        ]
    return normalized


def _derive_required_artifacts(artifact_ownership: Mapping[str, Any]) -> list[str]:
    if not artifact_ownership:
        return []
    artifacts: list[str] = []
    for key, value in artifact_ownership.items():
        name = _normalize_text(key, default="")
        if name in {"objective_contract", "completion_contract"}:
            continue
        artifact_name = _normalize_text(value, default="")
        if artifact_name:
            artifacts.append(artifact_name)
    return _dedupe(artifacts, sort_items=True)


def _derive_statuses(
    *,
    objective_summary: str,
    requested_outcome: str,
    in_scope: list[str],
    out_of_scope: list[str],
    acceptance_criteria: list[dict[str, Any]],
    required_artifacts: list[str],
    target_repo: str,
    target_branch: str,
    objective_source_status: str,
) -> tuple[str, str, str, str, list[str]]:
    blocked_reasons: list[str] = []

    if not objective_summary:
        blocked_reasons.append("objective_summary_missing")
    if not requested_outcome:
        blocked_reasons.append("requested_outcome_missing")
    if not target_repo:
        blocked_reasons.append("target_repo_missing")
    if not target_branch:
        blocked_reasons.append("target_branch_missing")

    defined_acceptance = [item for item in acceptance_criteria if _normalize_text(item.get("status")) == "defined"]
    undefined_acceptance = [item for item in acceptance_criteria if _normalize_text(item.get("status")) != "defined"]

    if objective_source_status == "missing":
        acceptance_status = "blocked"
        scope_status = "blocked"
        required_artifacts_status = "blocked"
        blocked_reasons.append("objective_sources_missing")
    else:
        if defined_acceptance and not undefined_acceptance:
            acceptance_status = "defined"
        elif defined_acceptance and undefined_acceptance:
            acceptance_status = "partially_defined"
            blocked_reasons.append("acceptance_partially_defined")
        elif undefined_acceptance:
            acceptance_status = "undefined"
            blocked_reasons.append("acceptance_undefined")
        else:
            acceptance_status = "undefined"
            blocked_reasons.append("acceptance_missing")

        if in_scope and out_of_scope:
            scope_status = "clear"
        elif in_scope and not out_of_scope:
            scope_status = "partial"
            blocked_reasons.append("scope_out_missing")
        elif not in_scope and out_of_scope:
            scope_status = "partial"
            blocked_reasons.append("scope_in_missing")
        else:
            scope_status = "unclear"
            blocked_reasons.append("scope_missing")

        if required_artifacts:
            required_artifacts_status = "defined"
        else:
            required_artifacts_status = "undefined"
            blocked_reasons.append("required_artifacts_missing")

    has_blocked = any(
        status == "blocked"
        for status in (acceptance_status, scope_status, required_artifacts_status)
    )
    if has_blocked:
        objective_status = "blocked"
    elif (
        acceptance_status == "defined"
        and scope_status == "clear"
        and required_artifacts_status == "defined"
        and objective_summary
        and requested_outcome
        and target_repo
        and target_branch
        and objective_source_status in {"structured_complete", "structured_partial"}
    ):
        objective_status = "complete"
    elif (
        objective_source_status in {"fallback_limited"}
        or not objective_summary
        or not requested_outcome
        or not target_repo
        or not target_branch
    ):
        objective_status = "incomplete"
    else:
        objective_status = "underspecified"

    blocked_reasons = _dedupe(blocked_reasons, sort_items=False)
    return objective_status, acceptance_status, scope_status, required_artifacts_status, blocked_reasons


def build_objective_contract_surface(
    *,
    run_id: str,
    artifacts: Mapping[str, Any] | None,
    units: list[Mapping[str, Any]] | None,
    policy_snapshot: Mapping[str, Any] | None = None,
    execution_repo_path: str | Path | None = None,
    artifact_ownership: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    artifacts_payload = dict(artifacts or {})
    units_payload = [item for item in (units or []) if isinstance(item, Mapping)]
    policy_payload = _as_mapping(policy_snapshot)

    project_brief = _as_mapping(artifacts_payload.get("project_brief"))
    repo_facts = _as_mapping(artifacts_payload.get("repo_facts"))
    pr_plan = _as_mapping(artifacts_payload.get("pr_plan"))
    roadmap = _as_mapping(artifacts_payload.get("roadmap"))
    pr_units = _collect_pr_plan_units(pr_plan)

    run_id_text = _normalize_text(run_id, default="")
    objective_base = _normalize_text(project_brief.get("project_id"), default="") or _normalize_text(
        pr_plan.get("plan_id"), default=""
    ) or run_id_text or "objective"
    objective_id = f"{objective_base}:objective"

    source_priority_used: list[int] = []
    structured_sources_present: list[str] = []
    free_text_supporting_notes: list[str] = []

    objective_summary_priority, objective_summary_source, objective_summary = _priority_pick(
        [
            (1, "project_brief.objective", _normalize_text(project_brief.get("objective"), default="")),
            (
                1,
                "pr_plan.prs.exact_scope",
                _normalize_text(pr_units[0].get("exact_scope"), default="") if pr_units else "",
            ),
            (
                2,
                "bounded_step_contract.purpose",
                _normalize_text(_as_mapping(units_payload[0].get("bounded_step_contract")).get("purpose"), default="")
                if units_payload
                else "",
            ),
            (
                2,
                "pr_implementation_prompt_contract.task_scope.purpose",
                _normalize_text(
                    _as_mapping(
                        _as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get("task_scope")
                    ).get("purpose"),
                    default="",
                )
                if units_payload
                else "",
            ),
        ]
    )
    if not objective_summary:
        free_text_supporting_notes = _collect_prompt_fallback_notes(units_payload)
        if free_text_supporting_notes:
            objective_summary = free_text_supporting_notes[0]
            objective_summary_source = "codex_task_prompt_md"
            objective_summary_priority = 4

    requested_outcome_priority, requested_outcome_source, requested_outcome = _priority_pick(
        [
            (
                1,
                "project_brief.success_definition",
                _normalize_text(project_brief.get("success_definition"), default=""),
            ),
            (
                1,
                "pr_plan.prs.acceptance_criteria",
                _first_list_item_text(pr_units[0].get("acceptance_criteria"))
                if pr_units
                else "",
            ),
            (
                2,
                "pr_implementation_prompt_contract.definition_of_done",
                _first_list_item_text(
                    _as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get("definition_of_done")
                )
                if units_payload
                else "",
            ),
        ]
    )

    objective_type_priority, objective_type_source, objective_type = _priority_pick(
        [
            (1, "project_brief.task_type", _normalize_text(project_brief.get("task_type"), default="")),
            (1, "pr_plan.plan_id", _normalize_text(pr_plan.get("plan_id"), default="")),
            (
                2,
                "pr_implementation_prompt_contract.task_scope.tier_category",
                _normalize_text(
                    _as_mapping(
                        _as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get("task_scope")
                    ).get("tier_category"),
                    default="",
                )
                if units_payload
                else "",
            ),
        ]
    )
    if not objective_type:
        objective_type = "planned_execution_objective"
        objective_type_source = "default"

    target_repo_priority, target_repo_source, target_repo = _priority_pick(
        [
            (1, "project_brief.target_repo", _normalize_text(project_brief.get("target_repo"), default="")),
            (1, "repo_facts.repo", _normalize_text(repo_facts.get("repo"), default="")),
            (
                2,
                "pr_implementation_prompt_contract.repository_context.target_repo",
                _normalize_text(
                    _as_mapping(
                        _as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get(
                            "repository_context"
                        )
                    ).get("target_repo"),
                    default="",
                )
                if units_payload
                else "",
            ),
            (3, "policy_snapshot.repository", _normalize_text(policy_payload.get("repository"), default="")),
            (
                3,
                "execution_repo_path.basename",
                _normalize_text(Path(str(execution_repo_path)).name, default="") if execution_repo_path else "",
            ),
        ]
    )

    target_branch_priority, target_branch_source, target_branch = _priority_pick(
        [
            (1, "project_brief.target_branch", _normalize_text(project_brief.get("target_branch"), default="")),
            (1, "repo_facts.default_branch", _normalize_text(repo_facts.get("default_branch"), default="")),
            (
                2,
                "pr_implementation_prompt_contract.repository_context.target_branch",
                _normalize_text(
                    _as_mapping(
                        _as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get(
                            "repository_context"
                        )
                    ).get("target_branch"),
                    default="",
                )
                if units_payload
                else "",
            ),
            (3, "policy_snapshot.base_branch", _normalize_text(policy_payload.get("base_branch"), default="")),
        ]
    )

    risk_priority, risk_source, requested_risk_tier = _priority_pick(
        [
            (
                1,
                "project_brief.allowed_risk_level",
                _normalize_text(project_brief.get("allowed_risk_level"), default=""),
            ),
            (1, "roadmap.estimated_risk", _normalize_text(roadmap.get("estimated_risk"), default="")),
            (1, "pr_plan.estimated_risk", _normalize_text(pr_plan.get("estimated_risk"), default="")),
            (
                2,
                "pr_implementation_prompt_contract.task_scope.tier_category",
                _normalize_text(
                    _as_mapping(
                        _as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get("task_scope")
                    ).get("tier_category"),
                    default="",
                )
                if units_payload
                else "",
            ),
        ]
    )

    pr_scope_in, pr_scope_out = _collect_scope_from_pr_plan(pr_units)
    contract_scope_in, contract_scope_out = _collect_scope_from_contracts(units_payload)
    in_scope = pr_scope_in or contract_scope_in
    out_of_scope = pr_scope_out or contract_scope_out

    forbidden_outcomes = _dedupe(
        _normalize_string_list(project_brief.get("non_goals"), sort_items=False)
        + _normalize_string_list(
            _as_mapping(_as_mapping(units_payload[0].get("pr_implementation_prompt_contract")).get("hard_constraints")).get(
                "non_goals"
            ),
            sort_items=False,
        )
        if units_payload
        else _normalize_string_list(project_brief.get("non_goals"), sort_items=False),
        sort_items=False,
    )

    acceptance_entries = _collect_acceptance_from_pr_plan(project_brief, pr_units) + _collect_acceptance_from_contracts(
        units_payload
    )
    acceptance_criteria = _normalize_acceptance_criteria(acceptance_entries)

    required_artifacts = _derive_required_artifacts(_as_mapping(artifact_ownership))

    field_priorities = [
        objective_summary_priority,
        requested_outcome_priority,
        objective_type_priority,
        target_repo_priority,
        target_branch_priority,
        risk_priority,
        1 if pr_scope_in else None,
        2 if (not pr_scope_in and contract_scope_in) else None,
        1 if pr_scope_out else None,
        2 if (not pr_scope_out and contract_scope_out) else None,
    ]
    source_priority_used = [priority for priority in field_priorities if isinstance(priority, int)]

    for priority, source in (
        (objective_summary_priority, objective_summary_source),
        (requested_outcome_priority, requested_outcome_source),
        (objective_type_priority, objective_type_source),
        (target_repo_priority, target_repo_source),
        (target_branch_priority, target_branch_source),
        (risk_priority, risk_source),
    ):
        if isinstance(priority, int) and priority <= 3 and source:
            structured_sources_present.append(source)

    structured_sources_present = _dedupe(structured_sources_present, sort_items=False)

    core_structured_complete = all(
        [
            objective_summary_priority in {1, 2, 3},
            requested_outcome_priority in {1, 2, 3},
            bool(in_scope),
            bool(out_of_scope),
            bool(acceptance_entries),
            target_repo_priority in {1, 2, 3},
            target_branch_priority in {1, 2, 3},
        ]
    )

    if core_structured_complete:
        objective_source_status = "structured_complete"
    elif structured_sources_present:
        objective_source_status = "structured_partial"
    elif free_text_supporting_notes:
        objective_source_status = "fallback_limited"
    else:
        objective_source_status = "missing"

    (
        objective_status,
        acceptance_status,
        scope_status,
        required_artifacts_status,
        blocked_reasons,
    ) = _derive_statuses(
        objective_summary=objective_summary,
        requested_outcome=requested_outcome,
        in_scope=in_scope,
        out_of_scope=out_of_scope,
        acceptance_criteria=acceptance_criteria,
        required_artifacts=required_artifacts,
        target_repo=target_repo,
        target_branch=target_branch,
        objective_source_status=objective_source_status,
    )

    source_priority_label = ""
    if source_priority_used:
        source_priority_label = f"priority_{min(source_priority_used)}"

    blocked_reason = blocked_reasons[0] if objective_status in {"blocked", "incomplete", "underspecified"} and blocked_reasons else ""

    payload = {
        "schema_version": OBJECTIVE_CONTRACT_SCHEMA_VERSION,
        "run_id": run_id_text,
        "objective_id": objective_id,
        "objective_summary": objective_summary,
        "objective_type": objective_type,
        "requested_outcome": requested_outcome,
        "in_scope": in_scope,
        "out_of_scope": out_of_scope,
        "acceptance_criteria": acceptance_criteria,
        "required_artifacts": required_artifacts,
        "forbidden_outcomes": forbidden_outcomes,
        "target_repo": target_repo,
        "target_branch": target_branch,
        "requested_risk_tier": requested_risk_tier,
        "objective_status": objective_status,
        "objective_source_status": objective_source_status,
        "acceptance_status": acceptance_status,
        "scope_status": scope_status,
        "required_artifacts_status": required_artifacts_status,
        "objective_blocked_reason": blocked_reason,
        "objective_blocked_reasons": blocked_reasons,
    }

    if source_priority_label:
        payload["source_priority_used"] = source_priority_label
    if structured_sources_present:
        payload["structured_sources_present"] = structured_sources_present
    if free_text_supporting_notes:
        payload["free_text_supporting_notes"] = free_text_supporting_notes

    return payload


def build_objective_run_state_summary_surface(
    objective_contract_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(objective_contract_payload or {})

    objective_status = _normalize_text(
        payload.get("objective_contract_status") if "objective_contract_status" in payload else payload.get("objective_status"),
        default="",
    )
    acceptance_status = _normalize_text(
        payload.get("objective_acceptance_status") if "objective_acceptance_status" in payload else payload.get("acceptance_status"),
        default="",
    )
    scope_status = _normalize_text(
        payload.get("objective_scope_status") if "objective_scope_status" in payload else payload.get("scope_status"),
        default="",
    )
    required_artifacts_status = _normalize_text(
        payload.get("objective_required_artifacts_status")
        if "objective_required_artifacts_status" in payload
        else payload.get("required_artifacts_status"),
        default="",
    )
    blocked_reason = _normalize_text(
        payload.get("objective_contract_blocked_reason")
        if "objective_contract_blocked_reason" in payload
        else payload.get("objective_blocked_reason"),
        default="",
    )

    present = bool(payload.get("objective_contract_present", False)) or bool(
        _normalize_text(payload.get("objective_id"), default="")
        or _normalize_text(payload.get("objective_summary"), default="")
        or objective_status
        or acceptance_status
        or scope_status
        or required_artifacts_status
    )

    if present and not objective_status:
        objective_status = "incomplete"
    if present and not acceptance_status:
        acceptance_status = "undefined"
    if present and not scope_status:
        scope_status = "unclear"
    if present and not required_artifacts_status:
        required_artifacts_status = "undefined"

    if (
        present
        and not blocked_reason
        and objective_status in {"blocked", "incomplete", "underspecified"}
    ):
        blocked_reason = "objective_contract_incomplete"

    return {
        "objective_contract_present": bool(present),
        "objective_id": _normalize_text(payload.get("objective_id"), default=""),
        "objective_summary": _normalize_text(payload.get("objective_summary"), default=""),
        "objective_type": _normalize_text(payload.get("objective_type"), default=""),
        "requested_outcome": _normalize_text(payload.get("requested_outcome"), default=""),
        "objective_acceptance_status": acceptance_status,
        "objective_required_artifacts_status": required_artifacts_status,
        "objective_scope_status": scope_status,
        "objective_contract_status": objective_status,
        "objective_contract_blocked_reason": blocked_reason,
    }

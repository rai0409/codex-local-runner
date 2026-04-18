from __future__ import annotations

from typing import Any
from typing import Mapping

PROMPT_CONTRACT_SCHEMA_VERSION = "v1"


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    if sort_items:
        return sorted(items)
    return items


def build_pr_implementation_prompt_contract(
    *,
    project_brief: Mapping[str, Any],
    repo_facts: Mapping[str, Any],
    pr_plan: Mapping[str, Any],
    bounded_step_contract: Mapping[str, Any],
    non_goals: list[str],
    constraints: list[str],
    required_tests: list[str],
    output_requirements: list[str],
) -> dict[str, Any]:
    step_id = _normalize_text(bounded_step_contract.get("step_id"), default="")
    title = _normalize_text(bounded_step_contract.get("title"), default="")
    purpose = _normalize_text(bounded_step_contract.get("purpose"), default="")
    scope_in = _normalize_string_list(bounded_step_contract.get("scope_in"), sort_items=True)
    scope_out = _normalize_string_list(bounded_step_contract.get("scope_out"), sort_items=True)
    acceptance = _normalize_string_list(bounded_step_contract.get("invariants_to_preserve"), sort_items=False)
    depends_on = _normalize_string_list(bounded_step_contract.get("depends_on"), sort_items=False)
    tier_category = _normalize_text(bounded_step_contract.get("tier_category"), default="")
    boundedness = (
        dict(bounded_step_contract.get("boundedness"))
        if isinstance(bounded_step_contract.get("boundedness"), Mapping)
        else {}
    )

    files_to_inspect = _normalize_string_list(
        bounded_step_contract.get("files_or_areas_to_inspect"),
        sort_items=True,
    ) or list(scope_in)

    return {
        "schema_version": PROMPT_CONTRACT_SCHEMA_VERSION,
        "source_step_id": step_id,
        "source_plan_id": _normalize_text(pr_plan.get("plan_id"), default=""),
        "task_scope": {
            "title": title,
            "purpose": purpose,
            "scope_in": list(scope_in),
            "scope_out": list(scope_out),
            "tier_category": tier_category,
            "depends_on": list(depends_on),
        },
        "repository_context": {
            "target_repo": _normalize_text(project_brief.get("target_repo"), default=""),
            "target_branch": _normalize_text(project_brief.get("target_branch"), default=""),
            "default_branch": _normalize_text(repo_facts.get("default_branch"), default=""),
            "relevant_paths": _normalize_string_list(repo_facts.get("relevant_paths"), sort_items=True),
        },
        "hard_constraints": {
            "non_goals": list(non_goals),
            "constraints": list(constraints),
        },
        "files_or_areas_to_inspect": list(files_to_inspect),
        "required_tests": list(required_tests),
        "definition_of_done": list(acceptance),
        "required_final_output": list(output_requirements),
        "step_boundedness": boundedness,
        "progression_metadata": {
            "planned_step_id": step_id,
            "strict_scope_files": list(scope_in),
            "forbidden_files": list(scope_out),
            "tier_category": tier_category,
            "depends_on": list(depends_on),
            "requires_explicit_validation": bool(required_tests),
            "scope_drift_detection_ready": True,
            "category_mismatch_detection_ready": bool(tier_category),
        },
        "human_review_notes": {
            "canonical_surface_notes": _normalize_string_list(pr_plan.get("canonical_surface_notes"), sort_items=False),
            "compatibility_notes": _normalize_string_list(pr_plan.get("compatibility_notes"), sort_items=False),
            "planning_warnings": _normalize_string_list(pr_plan.get("planning_warnings"), sort_items=False),
        },
    }

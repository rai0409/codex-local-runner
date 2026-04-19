from __future__ import annotations

from typing import Any
from typing import Mapping

PLANNED_STEP_CONTRACT_SCHEMA_VERSION = "v1"

BOUNDED_STATUS_BOUNDED = "bounded"
BOUNDED_STATUS_OVERSCOPED = "overscoped"
BOUNDED_STATUS_UNDERSPECIFIED = "underspecified"


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


def _derive_boundedness(*, contract: Mapping[str, Any], soft_file_cap: int) -> dict[str, Any]:
    issues: list[str] = []

    if not _normalize_text(contract.get("step_id"), default=""):
        issues.append("missing_step_id")
    if not _normalize_text(contract.get("title"), default=""):
        issues.append("missing_title")
    if not _normalize_text(contract.get("purpose"), default=""):
        issues.append("missing_purpose")
    if not _normalize_string_list(contract.get("scope_in"), sort_items=False):
        issues.append("missing_scope_in")
    if not _normalize_string_list(contract.get("validation_expectations"), sort_items=False):
        issues.append("missing_validation_expectations")

    scope_size = len(_normalize_string_list(contract.get("scope_in"), sort_items=False))
    if scope_size > soft_file_cap:
        issues.append(f"scope_in_exceeds_soft_file_cap:{soft_file_cap}")

    has_underspecified_issue = any(item.startswith("missing_") for item in issues)
    has_overscoped_issue = any(item.startswith("scope_in_exceeds_soft_file_cap:") for item in issues)
    if has_underspecified_issue:
        status = BOUNDED_STATUS_UNDERSPECIFIED
    elif has_overscoped_issue:
        status = BOUNDED_STATUS_OVERSCOPED
    else:
        status = BOUNDED_STATUS_BOUNDED

    return {
        "status": status,
        "issues": issues,
        "soft_file_cap": soft_file_cap,
        "is_bounded": status == BOUNDED_STATUS_BOUNDED,
    }


def build_bounded_planned_step_contract(
    pr: Mapping[str, Any],
    *,
    soft_file_cap: int = 6,
) -> dict[str, Any]:
    step_id = _normalize_text(pr.get("pr_id"), default="")
    scope_in = _normalize_string_list(pr.get("touched_files"), sort_items=True)
    scope_out = _normalize_string_list(pr.get("forbidden_files"), sort_items=True)
    title = _normalize_text(pr.get("title"), default="")
    purpose = _normalize_text(pr.get("exact_scope"), default="")
    invariants_to_preserve = _normalize_string_list(pr.get("acceptance_criteria"), sort_items=False)
    validation_expectations = _normalize_string_list(pr.get("validation_commands"), sort_items=False)
    depends_on = _normalize_string_list(pr.get("depends_on"), sort_items=False)
    tier_category = _normalize_text(pr.get("tier_category"), default="")
    rollback_notes = _normalize_text(pr.get("rollback_notes"), default="")

    contract = {
        "schema_version": PLANNED_STEP_CONTRACT_SCHEMA_VERSION,
        "step_id": step_id,
        "title": title,
        "purpose": purpose,
        "scope_in": scope_in,
        "scope_out": scope_out,
        "files_or_areas_to_inspect": list(scope_in),
        "invariants_to_preserve": invariants_to_preserve,
        "validation_expectations": validation_expectations,
        "rollback_notes": rollback_notes,
        "tier_category": tier_category,
        "depends_on": depends_on,
        "progression_metadata": {
            "planned_step_id": step_id,
            "tier_category": tier_category,
            "strict_scope_files": list(scope_in),
            "forbidden_files": list(scope_out),
            "depends_on": list(depends_on),
        },
    }
    contract["boundedness"] = _derive_boundedness(contract=contract, soft_file_cap=soft_file_cap)
    return contract

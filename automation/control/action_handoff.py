from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Callable
from typing import Mapping

from automation.control.execution_authority import ALL_FIRST_CLASS_ACTION_TOKENS
from automation.control.next_action_controller import ALLOWED_NEXT_ACTIONS
from automation.control.retry_context import normalize_retry_context

_HANDOFF_SCHEMA_VERSION = "v1"

_CONSUMABLE_ACTIONS = set(ALL_FIRST_CLASS_ACTION_TOKENS)

_UNSUPPORTED_ACTION_REASONS = {
}

_EVIDENCE_STATUS_ORDER = (
    "success",
    "empty",
    "not_found",
    "auth_failure",
    "api_failure",
    "unsupported_query",
)


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_non_negative_int(value: Any, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return max(0, int(text))
    return default


def _normalize_evidence_status(value: Any) -> str:
    status = _normalize_text(value, default="api_failure")
    if status in _EVIDENCE_STATUS_ORDER:
        return status
    return "api_failure"


def _extract_evidence_items(external_evidence: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(external_evidence, Mapping) or not external_evidence:
        return []

    if "status" in external_evidence:
        return [
            {
                "name": _normalize_text(
                    external_evidence.get("operation"),
                    default="external_evidence",
                ),
                "payload": dict(external_evidence),
            }
        ]

    items: list[dict[str, Any]] = []
    for key in sorted(external_evidence.keys(), key=lambda item: str(item)):
        value = external_evidence.get(key)
        if not isinstance(value, Mapping):
            continue
        items.append({"name": _normalize_text(key, default="external_evidence"), "payload": dict(value)})
    return items


def _derive_evidence_constraints(item: Mapping[str, Any]) -> list[str]:
    operation = _normalize_text(item.get("operation"), default="unknown_operation")
    status = _normalize_evidence_status(item.get("status"))
    data = item.get("data") if isinstance(item.get("data"), Mapping) else {}

    constraints: list[str] = []
    if status == "empty":
        constraints.append(f"github_evidence_empty:{operation}")
    elif status == "not_found":
        constraints.append(f"github_evidence_not_found:{operation}")
    elif status == "auth_failure":
        constraints.append(f"github_evidence_auth_failure:{operation}")
    elif status == "api_failure":
        constraints.append(f"github_evidence_api_failure:{operation}")
    elif status == "unsupported_query":
        constraints.append(f"github_evidence_unsupported_query:{operation}")

    if status == "success":
        if operation == "get_pr_status_summary":
            checks_state = _normalize_text(data.get("checks_state"), default="")
            if checks_state and checks_state != "passing":
                constraints.append(f"github_checks_state:{checks_state}")
        elif operation == "find_open_pr":
            if data.get("matched") is False:
                constraints.append("github_open_pr_not_matched")
        elif operation == "compare_refs":
            comparison_status = _normalize_text(data.get("comparison_status"), default="")
            if comparison_status in {"unknown", ""}:
                constraints.append("github_compare_inconclusive")
        elif operation == "get_branch_head":
            exists = data.get("exists")
            head_sha = _normalize_text(data.get("head_sha"), default="")
            if exists is False or not head_sha:
                constraints.append("github_branch_head_inconclusive")
    return constraints


def _summarize_external_evidence(external_evidence: Mapping[str, Any] | None) -> tuple[dict[str, Any], list[str]]:
    items = _extract_evidence_items(external_evidence)
    status_counts = {status: 0 for status in _EVIDENCE_STATUS_ORDER}
    constraints: set[str] = set()
    normalized_items: list[dict[str, Any]] = []
    for item in items:
        payload = item["payload"]
        status = _normalize_evidence_status(payload.get("status"))
        status_counts[status] += 1
        operation = _normalize_text(payload.get("operation"), default=item["name"])
        normalized_items.append(
            {
                "name": item["name"],
                "operation": operation,
                "status": status,
            }
        )
        for constraint in _derive_evidence_constraints(payload):
            if constraint:
                constraints.add(constraint)

    summary = {
        "provided": bool(items),
        "items_total": len(items),
        "items": normalized_items,
        "status_counts": status_counts,
    }
    return summary, sorted(constraints)


def _resolve_consumable(next_action: str) -> tuple[bool, str | None]:
    if next_action in _CONSUMABLE_ACTIONS:
        return True, None
    if next_action in _UNSUPPORTED_ACTION_REASONS:
        return False, _UNSUPPORTED_ACTION_REASONS[next_action]
    if next_action in ALLOWED_NEXT_ACTIONS:
        return False, "action is not mapped to a bounded executor in this phase"
    return False, f"unsupported next_action token: {next_action}"


def build_action_handoff_payload(
    *,
    job_id: str,
    decision_payload: Mapping[str, Any],
    now: Callable[[], datetime] = datetime.now,
    external_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    next_action = _normalize_text(decision_payload.get("next_action"), default="")
    reason = _normalize_text(decision_payload.get("reason"), default="")
    whether_human_required = bool(decision_payload.get("whether_human_required", False))
    normalized_retry_context = normalize_retry_context(
        decision_payload.get("updated_retry_context")
        if isinstance(decision_payload.get("updated_retry_context"), Mapping)
        else None
    )
    retry_budget_remaining = _as_non_negative_int(
        decision_payload.get("retry_budget_remaining"),
        default=_as_non_negative_int(normalized_retry_context.get("retry_budget_remaining"), default=0),
    )

    action_consumable, unsupported_reason = _resolve_consumable(next_action)
    evidence_summary, evidence_constraints = _summarize_external_evidence(external_evidence)

    retry_class = next_action if next_action in {"same_prompt_retry", "repair_prompt_retry"} else None
    return {
        "handoff_schema_version": _HANDOFF_SCHEMA_VERSION,
        "job_id": _normalize_text(job_id, default=""),
        "next_action": next_action,
        "reason": reason,
        "whether_human_required": whether_human_required,
        "retry_budget_remaining": retry_budget_remaining,
        "updated_retry_context": normalized_retry_context,
        "action_consumable": action_consumable,
        "unsupported_reason": unsupported_reason,
        "retry_class": retry_class,
        "evidence_summary": evidence_summary,
        "evidence_constraints": evidence_constraints,
        "handoff_created_at": _iso_now(now),
    }

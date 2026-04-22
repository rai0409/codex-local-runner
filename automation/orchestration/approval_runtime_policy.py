from __future__ import annotations

from typing import Any
from typing import Mapping

from automation.orchestration.approval_reply_commands import ALLOWED_REPLY_COMMANDS


APPROVAL_RUNTIME_RULES_SCHEMA_VERSION = "v1"
APPROVAL_RUNTIME_RULES_VERSION = "v1"

APPROVAL_RUNTIME_RULE_MODES = {
    "deterministic_rules_v1",
}
APPROVAL_RUNTIME_TEMPLATE_MODES = {
    "deterministic_templates_v1",
}
APPROVAL_RUNTIME_REPLY_MODES = {
    "fixed_command_grammar_v1",
}
APPROVAL_RUNTIME_TRUNCATION_MODES = {
    "compact_truncation_v1",
}

APPROVAL_RUNTIME_REASON_CODES = {
    "runtime_rules_ready",
    "runtime_rules_malformed_inputs",
    "runtime_rules_insufficient_truth",
    "runtime_rules_alias_deduplicated",
    "no_reason",
}

APPROVAL_RUNTIME_REASON_ORDER = (
    "runtime_rules_malformed_inputs",
    "runtime_rules_insufficient_truth",
    "runtime_rules_ready",
    "runtime_rules_alias_deduplicated",
    "no_reason",
)

APPROVAL_RUNTIME_RULES_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approval_runtime_rules_present",
)

APPROVAL_RUNTIME_RULES_SUMMARY_SAFE_FIELDS = (
    "runtime_rules_version",
    "direction_rule_mode",
    "email_template_mode",
    "reply_command_mode",
    "truncation_policy_mode",
    "runtime_rules_primary_reason",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = _normalize_text(value, default="")
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_reason_codes(values: list[str]) -> list[str]:
    normalized = [value for value in _ordered_unique(values) if value in APPROVAL_RUNTIME_REASON_CODES]
    return [value for value in APPROVAL_RUNTIME_REASON_ORDER if value in normalized]


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def build_approval_runtime_rules_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    approval_email_delivery_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    approval_email, approval_email_malformed = _coerce_mapping(approval_email_delivery_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)

    malformed_inputs = any((objective_malformed, approval_email_malformed, artifact_index_malformed))
    objective_id = _normalize_text(objective.get("objective_id"), default="")

    primary_reason = "runtime_rules_ready"
    if malformed_inputs:
        primary_reason = "runtime_rules_malformed_inputs"
    elif not objective_id:
        primary_reason = "runtime_rules_insufficient_truth"

    alias_deduplicated = bool(
        approval_email.get("retention_reference_consistent") is True
        and _normalize_text(approval_email.get("approval_email_status"), default="")
    )

    reason_codes = _normalize_reason_codes(
        [
            primary_reason,
            "runtime_rules_alias_deduplicated" if alias_deduplicated else "",
        ]
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    supporting_refs: list[str] = []
    if _normalize_text(approval_email.get("approval_email_status"), default=""):
        supporting_refs.append("approval_email_delivery_contract.approval_email_status")
    if _normalize_text(approval_email.get("proposed_next_direction"), default=""):
        supporting_refs.append("approval_email_delivery_contract.proposed_next_direction")
    if artifact_index:
        supporting_refs.append("contract_artifact_index")

    return {
        "schema_version": APPROVAL_RUNTIME_RULES_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "runtime_rules_version": APPROVAL_RUNTIME_RULES_VERSION,
        "direction_rule_mode": "deterministic_rules_v1",
        "email_template_mode": "deterministic_templates_v1",
        "reply_command_mode": "fixed_command_grammar_v1",
        "truncation_policy_mode": "compact_truncation_v1",
        "allowed_reply_commands": list(ALLOWED_REPLY_COMMANDS),
        "runtime_rules_primary_reason": reason_codes[0],
        "runtime_rules_reason_codes": reason_codes,
        "supporting_compact_truth_refs": _ordered_unique(supporting_refs),
    }


def build_approval_runtime_rules_run_state_summary_surface(
    approval_runtime_rules_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_runtime_rules_payload or {})
    return {
        "approval_runtime_rules_present": bool(
            _normalize_text(payload.get("runtime_rules_version"), default="")
        )
        or bool(payload.get("approval_runtime_rules_present"))
    }


def build_approval_runtime_rules_summary_surface(
    approval_runtime_rules_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_runtime_rules_payload or {})
    primary_reason = _normalize_text(payload.get("runtime_rules_primary_reason"), default="")
    if primary_reason not in APPROVAL_RUNTIME_REASON_CODES:
        primary_reason = "no_reason"
    return {
        "runtime_rules_version": _normalize_text(
            payload.get("runtime_rules_version"),
            default=APPROVAL_RUNTIME_RULES_VERSION,
        ),
        "direction_rule_mode": _normalize_text(
            payload.get("direction_rule_mode"),
            default="deterministic_rules_v1",
        ),
        "email_template_mode": _normalize_text(
            payload.get("email_template_mode"),
            default="deterministic_templates_v1",
        ),
        "reply_command_mode": _normalize_text(
            payload.get("reply_command_mode"),
            default="fixed_command_grammar_v1",
        ),
        "truncation_policy_mode": _normalize_text(
            payload.get("truncation_policy_mode"),
            default="compact_truncation_v1",
        ),
        "runtime_rules_primary_reason": primary_reason,
    }

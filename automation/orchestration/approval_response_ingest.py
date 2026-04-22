from __future__ import annotations

import importlib
import os
from typing import Any
from typing import Callable
from typing import Mapping

from automation.orchestration.approval_actor_policy import normalize_actor_class
from automation.orchestration.approval_reply_commands import is_supported_reply_command
from automation.orchestration.approval_reply_commands import map_approved_reply_command
from automation.orchestration.approval_reply_commands import normalize_reply_command
from automation.orchestration.approval_reply_commands import parse_reply_command


APPROVAL_RESPONSE_SCHEMA_VERSION = "v1"
APPROVED_RESTART_SCHEMA_VERSION = "v1"

APPROVAL_RESPONSE_STATUSES = {
    "awaiting_response",
    "response_received",
    "response_accepted",
    "response_rejected",
    "response_held",
    "response_unsupported",
    "insufficient_truth",
}

APPROVAL_RESPONSE_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

APPROVAL_RESPONSE_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

RESPONSE_DECISION_CLASSES = {
    "approved",
    "rejected",
    "held",
    "unsupported",
    "unknown",
}

RESPONSE_DECISION_SCOPES = {
    "restart_only",
    "direction_only",
    "restart_and_direction",
    "manual_review_only",
    "unknown",
}

APPROVED_RESTART_STATUSES = {
    "not_ready",
    "restart_allowed",
    "restart_blocked",
    "restart_held",
    "manual_followup_required",
    "insufficient_truth",
}

APPROVED_RESTART_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

APPROVED_RESTART_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

RESTART_DECISIONS = {
    "allow_same_lane_retry",
    "allow_repair_retry",
    "allow_truth_gathering",
    "allow_replan_preparation",
    "allow_closure_followup",
    "hold_restart",
    "block_restart",
    "manual_followup_only",
    "unknown",
}

_DOWNSTREAM_ADAPTERS = {
    "internal_automation",
    "none",
    "unknown",
}

APPROVAL_RESPONSE_REASON_CODES = {
    "malformed_response_inputs",
    "insufficient_response_truth",
    "awaiting_response",
    "unsupported_response_command",
    "response_hold_command",
    "response_reject_command",
    "response_actor_mismatch",
    "response_not_pending_review",
    "response_approved_accepted",
    "response_approved_incompatible_hard_block",
    "unknown_response_posture",
    "alias_deduplicated",
    "no_reason",
}

APPROVAL_RESPONSE_REASON_ORDER = (
    "malformed_response_inputs",
    "insufficient_response_truth",
    "awaiting_response",
    "unsupported_response_command",
    "response_hold_command",
    "response_reject_command",
    "response_actor_mismatch",
    "response_not_pending_review",
    "response_approved_incompatible_hard_block",
    "response_approved_accepted",
    "unknown_response_posture",
    "alias_deduplicated",
    "no_reason",
)

APPROVED_RESTART_REASON_CODES = {
    "malformed_restart_inputs",
    "insufficient_restart_truth",
    "restart_not_ready_no_response",
    "restart_blocked_unsupported_command",
    "restart_held_by_response",
    "restart_manual_followup_by_reject",
    "restart_retry_incompatible_with_truth",
    "restart_blocked_by_hard_posture",
    "restart_approved_and_allowed",
    "unknown_restart_posture",
    "alias_deduplicated",
    "no_reason",
}

APPROVED_RESTART_REASON_ORDER = (
    "malformed_restart_inputs",
    "insufficient_restart_truth",
    "restart_not_ready_no_response",
    "restart_blocked_unsupported_command",
    "restart_held_by_response",
    "restart_manual_followup_by_reject",
    "restart_retry_incompatible_with_truth",
    "restart_blocked_by_hard_posture",
    "restart_approved_and_allowed",
    "unknown_restart_posture",
    "alias_deduplicated",
    "no_reason",
)

_APPROVAL_RESPONSE_ALLOWED_SUPPORTING_REFS = (
    "approval_delivery_handoff_contract.approval_delivery_handoff_status",
    "approval_delivery_handoff_contract.delivery_mode",
    "approval_delivery_handoff_contract.delivery_outcome",
    "approval_delivery_handoff_contract.approval_pending_human_response",
    "approval_email_delivery_contract.approval_required",
    "approval_email_delivery_contract.proposed_next_direction",
    "approval_email_delivery_contract.proposed_restart_mode",
    "fleet_safety_control_contract.fleet_restart_decision",
)

_APPROVED_RESTART_ALLOWED_SUPPORTING_REFS = (
    "approval_response_contract.approval_response_status",
    "approval_response_contract.response_decision_class",
    "approval_email_delivery_contract.proposed_next_direction",
    "approval_email_delivery_contract.proposed_restart_mode",
    "fleet_safety_control_contract.fleet_restart_decision",
    "lane_stabilization_contract.current_lane",
    "failure_bucketing_hardening_contract.primary_failure_bucket",
    "failure_bucketing_hardening_contract.bucket_severity",
)

APPROVAL_RESPONSE_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approval_response_present",
)

APPROVED_RESTART_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approved_restart_present",
)

APPROVAL_RESPONSE_SUMMARY_SAFE_FIELDS = (
    "approval_response_status",
    "approval_response_validity",
    "approval_response_confidence",
    "response_command_normalized",
    "response_decision_class",
    "response_supported",
    "response_from_expected_actor",
    "approval_response_primary_reason",
)

APPROVED_RESTART_SUMMARY_SAFE_FIELDS = (
    "approved_restart_status",
    "approved_restart_validity",
    "approved_restart_confidence",
    "restart_decision",
    "restart_allowed",
    "restart_blocked",
    "restart_held",
    "restart_requires_manual_followup",
    "approved_next_direction",
    "approved_restart_primary_reason",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes"}:
            return True
        if lowered in {"0", "false", "no"}:
            return False
    return False


def _normalize_enum(value: Any, *, allowed: set[str], default: str) -> str:
    text = _normalize_text(value, default="")
    if text in allowed:
        return text
    return default


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


def _normalize_supporting_refs(values: list[str], *, allowed: tuple[str, ...]) -> list[str]:
    allowed_set = set(allowed)
    return [value for value in _ordered_unique(values) if value in allowed_set]


def _normalize_reason_codes(values: list[str], *, allowed: set[str], order: tuple[str, ...]) -> list[str]:
    normalized = [value for value in _ordered_unique(values) if value in allowed]
    ordered = [value for value in order if value in normalized]
    return ordered if ordered else ["no_reason"]


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _load_response_adapter_from_env() -> Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None:
    target = _normalize_text(os.getenv("INTERNAL_AUTOMATION_APPROVAL_RESPONSE_ADAPTER"), default="")
    if not target or ":" not in target:
        return None
    module_name, function_name = target.split(":", 1)
    module_name = module_name.strip()
    function_name = function_name.strip()
    if not module_name or not function_name:
        return None
    try:
        module = importlib.import_module(module_name)
        candidate = getattr(module, function_name)
    except Exception:
        return None
    return candidate if callable(candidate) else None


def _invoke_response_adapter(
    *,
    request_payload: Mapping[str, Any],
    adapter: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> dict[str, Any]:
    resolved_adapter = adapter or _load_response_adapter_from_env()
    if resolved_adapter is None:
        return {
            "response_received": False,
            "response_command_raw": "",
            "response_message_id": "",
            "response_received_timestamp": "",
            "response_actor_class": "unknown",
            "downstream_adapter": "none",
            "adapter_error": "",
        }
    try:
        raw = resolved_adapter(dict(request_payload))
    except Exception as exc:
        return {
            "response_received": False,
            "response_command_raw": "",
            "response_message_id": "",
            "response_received_timestamp": "",
            "response_actor_class": "unknown",
            "downstream_adapter": "internal_automation",
            "adapter_error": _normalize_text(str(exc), default="adapter_error"),
        }
    payload = dict(raw) if isinstance(raw, Mapping) else {}
    return {
        "response_received": _normalize_bool(payload.get("response_received")),
        "response_command_raw": _normalize_text(payload.get("response_command_raw"), default=""),
        "response_message_id": _normalize_text(payload.get("response_message_id"), default=""),
        "response_received_timestamp": _normalize_text(
            payload.get("response_received_timestamp"),
            default="",
        ),
        "response_actor_class": normalize_actor_class(payload.get("response_actor_class")),
        "downstream_adapter": _normalize_enum(
            payload.get("downstream_adapter"),
            allowed=_DOWNSTREAM_ADAPTERS,
            default="internal_automation",
        ),
        "adapter_error": _normalize_text(payload.get("adapter_error"), default=""),
    }


def _is_durable_review_outcome(delivery_outcome: str) -> bool:
    return delivery_outcome in {"draft_created", "sent", "queued_for_review"}


def build_approval_response_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    approval_delivery_handoff_payload: Mapping[str, Any] | None,
    approval_email_delivery_payload: Mapping[str, Any] | None,
    approval_runtime_rules_payload: Mapping[str, Any] | None,
    fleet_safety_control_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
    response_payload: Mapping[str, Any] | None = None,
    response_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    handoff, handoff_malformed = _coerce_mapping(approval_delivery_handoff_payload)
    approval_email, approval_email_malformed = _coerce_mapping(approval_email_delivery_payload)
    runtime_rules, runtime_rules_malformed = _coerce_mapping(approval_runtime_rules_payload)
    fleet, fleet_malformed = _coerce_mapping(fleet_safety_control_payload)
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)
    provided_response, provided_response_malformed = _coerce_mapping(response_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            handoff_malformed,
            approval_email_malformed,
            runtime_rules_malformed,
            fleet_malformed,
            run_state_malformed,
            artifact_index_malformed,
            provided_response_malformed,
        )
    )

    objective_id = _normalize_text(objective.get("objective_id"), default="")
    approval_required = _normalize_bool(approval_email.get("approval_required"))
    approval_priority = _normalize_text(approval_email.get("approval_priority"), default="unknown")
    proposed_next_direction = _normalize_text(
        approval_email.get("proposed_next_direction"),
        default="unknown",
    )
    proposed_target_lane = _normalize_text(
        approval_email.get("proposed_target_lane"),
        default="unknown",
    )
    proposed_restart_mode = _normalize_text(
        approval_email.get("proposed_restart_mode"),
        default="unknown",
    )
    fleet_restart_decision = _normalize_text(
        fleet.get("fleet_restart_decision"),
        default="unknown",
    )

    delivery_mode = _normalize_text(handoff.get("delivery_mode"), default="unknown")
    if not delivery_mode:
        delivery_mode = _normalize_text(approval_email.get("delivery_mode"), default="unknown")
    delivery_outcome = _normalize_text(handoff.get("delivery_outcome"), default="unknown")
    approval_pending_human_response = _normalize_bool(
        handoff.get("approval_pending_human_response")
    )
    durable_review_outcome = _is_durable_review_outcome(delivery_outcome)

    downstream_delivery_id = _normalize_text(handoff.get("downstream_delivery_id"), default="")
    downstream_thread_id = _normalize_text(handoff.get("downstream_thread_id"), default="")
    downstream_message_id = _normalize_text(handoff.get("downstream_message_id"), default="")
    downstream_adapter = _normalize_enum(
        handoff.get("downstream_adapter"),
        allowed=_DOWNSTREAM_ADAPTERS,
        default="unknown",
    )
    if downstream_adapter == "unknown" and runtime_rules:
        downstream_adapter = "internal_automation"

    effective_response = (
        dict(provided_response)
        if provided_response
        else _invoke_response_adapter(
            request_payload={
                "run_id": _normalize_text(run_id, default=""),
                "downstream_delivery_id": downstream_delivery_id,
                "downstream_thread_id": downstream_thread_id,
                "downstream_message_id": downstream_message_id,
                "delivery_mode": delivery_mode,
            },
            adapter=response_adapter,
        )
    )

    response_command_raw = _normalize_text(
        effective_response.get("response_command_raw"),
        default="",
    )
    parsed_response = parse_reply_command(response_command_raw)
    response_command_normalized = _normalize_text(
        parsed_response.get("normalized"),
        default="",
    )
    response_supported = bool(parsed_response.get("supported")) and is_supported_reply_command(
        response_command_normalized
    )
    response_received = _normalize_bool(effective_response.get("response_received")) or bool(
        response_command_raw
    )
    response_message_id = _normalize_text(
        effective_response.get("response_message_id"),
        default="",
    )
    response_received_timestamp = _normalize_text(
        effective_response.get("response_received_timestamp"),
        default="",
    )
    response_actor_class = normalize_actor_class(effective_response.get("response_actor_class"))
    expected_actor_class = normalize_actor_class(approval_email.get("recipient_class"))

    actor_enforced = expected_actor_class != "unknown" and response_actor_class != "unknown"
    response_from_expected_actor = (
        expected_actor_class == response_actor_class if actor_enforced else True
    )

    review_context_ready = approval_pending_human_response or durable_review_outcome
    response_acceptable = bool(
        response_received
        and response_supported
        and response_from_expected_actor
        and review_context_ready
    )

    mapped = map_approved_reply_command(response_command_normalized)
    mapped_decision = _normalize_text(mapped.get("approval_decision"), default="unknown")

    decision_class = "unknown"
    decision_scope = "unknown"
    response_blocks_restart = False
    response_holds_restart = False
    response_allows_restart = False
    lead_reason = "unknown_response_posture"
    status = "awaiting_response"
    validity = "valid"
    confidence = "medium"

    insufficient_truth = not objective_id or (
        approval_required and _normalize_text(handoff.get("approval_delivery_handoff_status"), default="")
        in {"", "insufficient_truth"}
    )

    if malformed_inputs:
        lead_reason = "malformed_response_inputs"
        status = "insufficient_truth"
        validity = "malformed"
        confidence = "low"
    elif insufficient_truth:
        lead_reason = "insufficient_response_truth"
        status = "insufficient_truth"
        validity = "insufficient_truth"
        confidence = "low"
    elif not response_received:
        lead_reason = "awaiting_response"
        status = "awaiting_response"
        validity = "valid"
        confidence = "high"
    elif not response_supported:
        lead_reason = "unsupported_response_command"
        status = "response_unsupported"
        decision_class = "unsupported"
        decision_scope = "unknown"
        response_blocks_restart = True
        validity = "valid"
        confidence = "high"
    elif not response_from_expected_actor:
        lead_reason = "response_actor_mismatch"
        status = "response_received"
        decision_class = "unknown"
        decision_scope = "manual_review_only"
        response_blocks_restart = True
        validity = "partial"
        confidence = "medium"
    elif not review_context_ready:
        lead_reason = "response_not_pending_review"
        status = "response_received"
        decision_class = "unknown"
        decision_scope = "unknown"
        response_blocks_restart = True
        validity = "partial"
        confidence = "medium"
    elif mapped_decision == "held":
        lead_reason = "response_hold_command"
        status = "response_held"
        decision_class = "held"
        decision_scope = "restart_only"
        response_holds_restart = True
        validity = "valid"
        confidence = "high"
    elif mapped_decision == "rejected":
        lead_reason = "response_reject_command"
        status = "response_rejected"
        decision_class = "rejected"
        decision_scope = "manual_review_only"
        response_blocks_restart = True
        validity = "valid"
        confidence = "high"
    elif mapped_decision == "approved" and response_acceptable:
        lead_reason = "response_approved_accepted"
        status = "response_accepted"
        decision_class = "approved"
        decision_scope = "restart_and_direction"
        response_allows_restart = True
        validity = "valid"
        confidence = "high"
    else:
        lead_reason = "unknown_response_posture"
        status = "response_received"
        decision_class = "unknown"
        decision_scope = "unknown"
        response_blocks_restart = True
        validity = "partial"
        confidence = "low"

    if mapped_decision == "approved" and response_acceptable and fleet_restart_decision in {
        "restart_blocked",
        "manual_only",
    } and not _normalize_bool(handoff.get("approval_can_clear_restart_block")):
        lead_reason = "response_approved_incompatible_hard_block"
        response_allows_restart = False
        response_blocks_restart = True

    alias_deduplicated = _normalize_bool(run_state.get("retention_alias_deduplicated"))
    reason_codes = _normalize_reason_codes(
        [
            lead_reason,
            "alias_deduplicated" if alias_deduplicated else "",
        ],
        allowed=APPROVAL_RESPONSE_REASON_CODES,
        order=APPROVAL_RESPONSE_REASON_ORDER,
    )

    supporting_refs = _normalize_supporting_refs(
        [
            "approval_delivery_handoff_contract.approval_delivery_handoff_status"
            if _normalize_text(handoff.get("approval_delivery_handoff_status"), default="")
            else "",
            "approval_delivery_handoff_contract.delivery_mode" if delivery_mode else "",
            "approval_delivery_handoff_contract.delivery_outcome" if delivery_outcome else "",
            "approval_delivery_handoff_contract.approval_pending_human_response"
            if "approval_pending_human_response" in handoff
            else "",
            "approval_email_delivery_contract.approval_required" if "approval_required" in approval_email else "",
            "approval_email_delivery_contract.proposed_next_direction"
            if _normalize_text(approval_email.get("proposed_next_direction"), default="")
            else "",
            "approval_email_delivery_contract.proposed_restart_mode"
            if _normalize_text(approval_email.get("proposed_restart_mode"), default="")
            else "",
            "fleet_safety_control_contract.fleet_restart_decision" if fleet_restart_decision else "",
        ],
        allowed=_APPROVAL_RESPONSE_ALLOWED_SUPPORTING_REFS,
    )

    return {
        "schema_version": APPROVAL_RESPONSE_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "approval_response_status": _normalize_enum(
            status,
            allowed=APPROVAL_RESPONSE_STATUSES,
            default="insufficient_truth",
        ),
        "approval_response_validity": _normalize_enum(
            validity,
            allowed=APPROVAL_RESPONSE_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_response_confidence": _normalize_enum(
            confidence,
            allowed=APPROVAL_RESPONSE_CONFIDENCE_LEVELS,
            default="low",
        ),
        "response_received": bool(response_received),
        "response_command_raw": response_command_raw,
        "response_command_normalized": response_command_normalized,
        "response_supported": bool(response_supported),
        "response_from_expected_actor": bool(response_from_expected_actor),
        "response_decision_class": _normalize_enum(
            decision_class,
            allowed=RESPONSE_DECISION_CLASSES,
            default="unknown",
        ),
        "response_decision_scope": _normalize_enum(
            decision_scope,
            allowed=RESPONSE_DECISION_SCOPES,
            default="unknown",
        ),
        "response_blocks_restart": bool(response_blocks_restart),
        "response_holds_restart": bool(response_holds_restart),
        "response_allows_restart": bool(response_allows_restart),
        "downstream_adapter": _normalize_enum(
            downstream_adapter,
            allowed=_DOWNSTREAM_ADAPTERS,
            default="unknown",
        ),
        "downstream_delivery_id": downstream_delivery_id,
        "downstream_thread_id": downstream_thread_id,
        "downstream_message_id": downstream_message_id,
        "response_message_id": response_message_id,
        "response_received_timestamp": response_received_timestamp,
        "approval_response_primary_reason": reason_codes[0],
        "approval_response_reason_codes": reason_codes,
        "approval_delivery_handoff_status": _normalize_text(
            handoff.get("approval_delivery_handoff_status"),
            default="insufficient_truth",
        ),
        "delivery_mode": _normalize_text(delivery_mode, default="unknown"),
        "delivery_outcome": _normalize_text(delivery_outcome, default="unknown"),
        "approval_pending_human_response": bool(approval_pending_human_response),
        "approval_required": bool(approval_required),
        "approval_priority": approval_priority,
        "proposed_next_direction": proposed_next_direction,
        "proposed_target_lane": proposed_target_lane,
        "proposed_restart_mode": proposed_restart_mode,
        "fleet_restart_decision": fleet_restart_decision,
        "supporting_compact_truth_refs": supporting_refs,
        "next_safe_hint": _normalize_text(run_state.get("next_safe_action"), default=""),
        "closure_followup_hint": _normalize_text(
            run_state.get("closure_followup_hint"),
            default="",
        ),
        "retry_hint": _normalize_text(run_state.get("retry_hint"), default=""),
        "reentry_hint": _normalize_text(run_state.get("reentry_hint"), default=""),
    }


def build_approved_restart_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    approval_response_payload: Mapping[str, Any] | None,
    approval_delivery_handoff_payload: Mapping[str, Any] | None,
    approval_email_delivery_payload: Mapping[str, Any] | None,
    fleet_safety_control_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    response, response_malformed = _coerce_mapping(approval_response_payload)
    handoff, handoff_malformed = _coerce_mapping(approval_delivery_handoff_payload)
    approval_email, approval_email_malformed = _coerce_mapping(approval_email_delivery_payload)
    fleet, fleet_malformed = _coerce_mapping(fleet_safety_control_payload)
    hard_bucket, hard_bucket_malformed = _coerce_mapping(failure_bucketing_hardening_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)
    _ = artifact_index

    malformed_inputs = any(
        (
            objective_malformed,
            response_malformed,
            handoff_malformed,
            approval_email_malformed,
            fleet_malformed,
            hard_bucket_malformed,
            lane_malformed,
            run_state_malformed,
            artifact_index_malformed,
        )
    )

    objective_id = _normalize_text(objective.get("objective_id"), default="")
    approval_response_status = _normalize_text(
        response.get("approval_response_status"),
        default="insufficient_truth",
    )
    response_received = _normalize_bool(response.get("response_received"))
    response_command_normalized = normalize_reply_command(
        response.get("response_command_normalized") or response.get("response_command_raw")
    )
    response_decision_class = _normalize_enum(
        response.get("response_decision_class"),
        allowed=RESPONSE_DECISION_CLASSES,
        default="unknown",
    )
    approval_required = _normalize_bool(approval_email.get("approval_required"))

    proposed_next_direction = _normalize_text(
        approval_email.get("proposed_next_direction"),
        default="unknown",
    )
    proposed_target_lane = _normalize_text(
        approval_email.get("proposed_target_lane"),
        default="unknown",
    )
    proposed_restart_mode = _normalize_text(
        approval_email.get("proposed_restart_mode"),
        default="unknown",
    )
    fleet_restart_decision = _normalize_text(
        fleet.get("fleet_restart_decision"),
        default="unknown",
    )
    current_lane = _normalize_text(lane.get("current_lane"), default="unknown")
    primary_failure_bucket = _normalize_text(
        hard_bucket.get("primary_failure_bucket"),
        default="unknown",
    )
    bucket_severity = _normalize_text(hard_bucket.get("bucket_severity"), default="unknown")

    approval_can_clear_restart_block = _normalize_bool(
        response.get("approval_can_clear_restart_block")
    ) or _normalize_bool(handoff.get("approval_can_clear_restart_block"))
    pending_block = _normalize_bool(handoff.get("restart_blocked_pending_approval"))
    pending_hold = _normalize_bool(handoff.get("restart_held_pending_approval"))
    fleet_block = fleet_restart_decision in {"restart_blocked", "manual_only"}
    fleet_hold = fleet_restart_decision == "restart_hold"

    response_blocks_restart = _normalize_bool(response.get("response_blocks_restart"))
    response_holds_restart = _normalize_bool(response.get("response_holds_restart"))

    mapped = map_approved_reply_command(response_command_normalized)
    mapped_next_direction = _normalize_text(mapped.get("proposed_next_direction"), default="unknown")
    mapped_target_lane = _normalize_text(mapped.get("proposed_target_lane"), default="unknown")
    mapped_restart_mode = _normalize_text(mapped.get("proposed_restart_mode"), default="unknown")
    mapped_action_class = _normalize_text(mapped.get("proposed_action_class"), default="unknown")

    restart_decision = "unknown"
    restart_allowed = False
    restart_blocked = False
    restart_held = False
    restart_requires_manual_followup = False
    approved_next_direction = "unknown"
    approved_target_lane = "unknown"
    approved_restart_mode = "unknown"
    approved_action_class = "unknown"
    lead_reason = "unknown_restart_posture"
    status = "not_ready"
    validity = "valid"
    confidence = "medium"

    insufficient_truth = not objective_id or approval_response_status == "insufficient_truth"
    hard_block_uncleared = (pending_block or fleet_block) and not approval_can_clear_restart_block
    hard_hold_uncleared = (pending_hold or fleet_hold) and not approval_can_clear_restart_block

    retry_incompatible = bool(
        response_command_normalized == "OK RETRY"
        and proposed_next_direction not in {"same_lane_retry", "repair_retry"}
    )

    if malformed_inputs:
        lead_reason = "malformed_restart_inputs"
        status = "insufficient_truth"
        validity = "malformed"
        confidence = "low"
    elif insufficient_truth:
        lead_reason = "insufficient_restart_truth"
        status = "insufficient_truth"
        validity = "insufficient_truth"
        confidence = "low"
    elif not response_received or approval_response_status == "awaiting_response":
        lead_reason = "restart_not_ready_no_response"
        status = "not_ready"
        validity = "valid"
        confidence = "high"
    elif response_decision_class == "unsupported":
        lead_reason = "restart_blocked_unsupported_command"
        status = "restart_blocked"
        restart_decision = "block_restart"
        restart_blocked = True
        validity = "valid"
        confidence = "high"
    elif response_decision_class == "held" or response_holds_restart:
        lead_reason = "restart_held_by_response"
        status = "restart_held"
        restart_decision = "hold_restart"
        restart_held = True
        validity = "valid"
        confidence = "high"
    elif response_decision_class == "rejected":
        lead_reason = "restart_manual_followup_by_reject"
        status = "manual_followup_required"
        restart_decision = "manual_followup_only"
        restart_requires_manual_followup = True
        validity = "valid"
        confidence = "high"
    elif response_decision_class == "approved":
        if retry_incompatible:
            lead_reason = "restart_retry_incompatible_with_truth"
            status = "restart_blocked"
            restart_decision = "block_restart"
            restart_blocked = True
            validity = "partial"
            confidence = "medium"
        elif hard_block_uncleared or response_blocks_restart:
            lead_reason = "restart_blocked_by_hard_posture"
            status = "restart_blocked"
            restart_decision = "block_restart"
            restart_blocked = True
            validity = "partial"
            confidence = "medium"
        elif hard_hold_uncleared:
            lead_reason = "restart_held_by_response"
            status = "restart_held"
            restart_decision = "hold_restart"
            restart_held = True
            validity = "valid"
            confidence = "medium"
        else:
            lead_reason = "restart_approved_and_allowed"
            status = "restart_allowed"
            restart_allowed = True
            validity = "valid"
            confidence = "high"
            if response_command_normalized == "OK RETRY":
                if proposed_next_direction == "repair_retry":
                    approved_next_direction = "repair_retry"
                    approved_target_lane = proposed_target_lane or "bounded_local_patch"
                    approved_restart_mode = "approval_required_then_restart"
                    approved_action_class = "review_and_restart"
                    restart_decision = "allow_repair_retry"
                else:
                    approved_next_direction = "same_lane_retry"
                    approved_target_lane = proposed_target_lane or "bounded_local_patch"
                    approved_restart_mode = "approval_required_then_restart"
                    approved_action_class = "review_and_restart"
                    restart_decision = "allow_same_lane_retry"
            elif response_command_normalized == "OK REPLAN":
                approved_next_direction = "replan_preparation"
                approved_target_lane = "replan_preparation"
                approved_restart_mode = "approval_required_then_restart"
                approved_action_class = "review_and_replan"
                restart_decision = "allow_replan_preparation"
            elif response_command_normalized == "OK TRUTH":
                approved_next_direction = "truth_gathering"
                approved_target_lane = "truth_gathering"
                approved_restart_mode = "approval_required_then_restart"
                approved_action_class = "review_and_recollect"
                restart_decision = "allow_truth_gathering"
            elif response_command_normalized == "OK CLOSE":
                approved_next_direction = "closure_followup"
                approved_target_lane = "closure_followup"
                approved_restart_mode = "approval_required_then_restart"
                approved_action_class = "review_and_close_followup"
                restart_decision = "allow_closure_followup"
            else:
                approved_next_direction = mapped_next_direction
                approved_target_lane = mapped_target_lane
                approved_restart_mode = mapped_restart_mode
                approved_action_class = mapped_action_class
                restart_decision = "unknown"
    else:
        lead_reason = "unknown_restart_posture"
        status = "restart_blocked"
        restart_decision = "block_restart"
        restart_blocked = True
        validity = "partial"
        confidence = "low"

    alias_deduplicated = _normalize_bool(run_state.get("retention_alias_deduplicated"))
    reason_codes = _normalize_reason_codes(
        [
            lead_reason,
            "alias_deduplicated" if alias_deduplicated else "",
        ],
        allowed=APPROVED_RESTART_REASON_CODES,
        order=APPROVED_RESTART_REASON_ORDER,
    )

    supporting_refs = _normalize_supporting_refs(
        [
            "approval_response_contract.approval_response_status"
            if approval_response_status
            else "",
            "approval_response_contract.response_decision_class"
            if response_decision_class
            else "",
            "approval_email_delivery_contract.proposed_next_direction"
            if proposed_next_direction
            else "",
            "approval_email_delivery_contract.proposed_restart_mode"
            if proposed_restart_mode
            else "",
            "fleet_safety_control_contract.fleet_restart_decision" if fleet_restart_decision else "",
            "lane_stabilization_contract.current_lane" if current_lane else "",
            "failure_bucketing_hardening_contract.primary_failure_bucket" if primary_failure_bucket else "",
            "failure_bucketing_hardening_contract.bucket_severity" if bucket_severity else "",
        ],
        allowed=_APPROVED_RESTART_ALLOWED_SUPPORTING_REFS,
    )

    return {
        "schema_version": APPROVED_RESTART_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "approved_restart_status": _normalize_enum(
            status,
            allowed=APPROVED_RESTART_STATUSES,
            default="insufficient_truth",
        ),
        "approved_restart_validity": _normalize_enum(
            validity,
            allowed=APPROVED_RESTART_VALIDITIES,
            default="insufficient_truth",
        ),
        "approved_restart_confidence": _normalize_enum(
            confidence,
            allowed=APPROVED_RESTART_CONFIDENCE_LEVELS,
            default="low",
        ),
        "restart_decision": _normalize_enum(
            restart_decision,
            allowed=RESTART_DECISIONS,
            default="unknown",
        ),
        "restart_allowed": bool(restart_allowed),
        "restart_blocked": bool(restart_blocked),
        "restart_held": bool(restart_held),
        "restart_requires_manual_followup": bool(restart_requires_manual_followup),
        "approved_next_direction": approved_next_direction,
        "approved_target_lane": approved_target_lane,
        "approved_restart_mode": approved_restart_mode,
        "approved_action_class": approved_action_class,
        "response_command_normalized": response_command_normalized,
        "response_decision_class": response_decision_class,
        "approval_can_clear_restart_block": bool(approval_can_clear_restart_block),
        "approved_restart_primary_reason": reason_codes[0],
        "approved_restart_reason_codes": reason_codes,
        "approval_response_status": approval_response_status,
        "approval_required": bool(approval_required),
        "proposed_next_direction": proposed_next_direction,
        "proposed_target_lane": proposed_target_lane,
        "proposed_restart_mode": proposed_restart_mode,
        "fleet_restart_decision": fleet_restart_decision,
        "current_lane": current_lane,
        "primary_failure_bucket": primary_failure_bucket,
        "bucket_severity": bucket_severity,
        "supporting_compact_truth_refs": supporting_refs,
        "next_safe_hint": _normalize_text(run_state.get("next_safe_action"), default=""),
        "closure_followup_hint": _normalize_text(
            run_state.get("closure_followup_hint"),
            default="",
        ),
        "retry_hint": _normalize_text(run_state.get("retry_hint"), default=""),
        "reentry_hint": _normalize_text(run_state.get("reentry_hint"), default=""),
    }


def build_approval_response_run_state_summary_surface(
    approval_response_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_response_payload or {})
    return {
        "approval_response_present": bool(
            _normalize_text(payload.get("approval_response_status"), default="")
        )
        or _normalize_bool(payload.get("approval_response_present"))
    }


def build_approved_restart_run_state_summary_surface(
    approved_restart_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approved_restart_payload or {})
    return {
        "approved_restart_present": bool(
            _normalize_text(payload.get("approved_restart_status"), default="")
        )
        or _normalize_bool(payload.get("approved_restart_present"))
    }


def build_approval_response_summary_surface(
    approval_response_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_response_payload or {})
    return {
        "approval_response_status": _normalize_enum(
            payload.get("approval_response_status"),
            allowed=APPROVAL_RESPONSE_STATUSES,
            default="insufficient_truth",
        ),
        "approval_response_validity": _normalize_enum(
            payload.get("approval_response_validity"),
            allowed=APPROVAL_RESPONSE_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_response_confidence": _normalize_enum(
            payload.get("approval_response_confidence"),
            allowed=APPROVAL_RESPONSE_CONFIDENCE_LEVELS,
            default="low",
        ),
        "response_command_normalized": normalize_reply_command(
            payload.get("response_command_normalized")
        ),
        "response_decision_class": _normalize_enum(
            payload.get("response_decision_class"),
            allowed=RESPONSE_DECISION_CLASSES,
            default="unknown",
        ),
        "response_supported": _normalize_bool(payload.get("response_supported")),
        "response_from_expected_actor": _normalize_bool(
            payload.get("response_from_expected_actor")
        ),
        "approval_response_primary_reason": _normalize_text(
            payload.get("approval_response_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("approval_response_primary_reason"), default="")
        in APPROVAL_RESPONSE_REASON_CODES
        else "no_reason",
    }


def build_approved_restart_summary_surface(
    approved_restart_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approved_restart_payload or {})
    return {
        "approved_restart_status": _normalize_enum(
            payload.get("approved_restart_status"),
            allowed=APPROVED_RESTART_STATUSES,
            default="insufficient_truth",
        ),
        "approved_restart_validity": _normalize_enum(
            payload.get("approved_restart_validity"),
            allowed=APPROVED_RESTART_VALIDITIES,
            default="insufficient_truth",
        ),
        "approved_restart_confidence": _normalize_enum(
            payload.get("approved_restart_confidence"),
            allowed=APPROVED_RESTART_CONFIDENCE_LEVELS,
            default="low",
        ),
        "restart_decision": _normalize_enum(
            payload.get("restart_decision"),
            allowed=RESTART_DECISIONS,
            default="unknown",
        ),
        "restart_allowed": _normalize_bool(payload.get("restart_allowed")),
        "restart_blocked": _normalize_bool(payload.get("restart_blocked")),
        "restart_held": _normalize_bool(payload.get("restart_held")),
        "restart_requires_manual_followup": _normalize_bool(
            payload.get("restart_requires_manual_followup")
        ),
        "approved_next_direction": _normalize_text(
            payload.get("approved_next_direction"),
            default="unknown",
        ),
        "approved_restart_primary_reason": _normalize_text(
            payload.get("approved_restart_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(payload.get("approved_restart_primary_reason"), default="")
        in APPROVED_RESTART_REASON_CODES
        else "no_reason",
    }


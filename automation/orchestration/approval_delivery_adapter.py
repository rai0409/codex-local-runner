from __future__ import annotations

import importlib
import os
from typing import Any
from typing import Callable
from typing import Mapping


APPROVAL_DELIVERY_HANDOFF_SCHEMA_VERSION = "v1"

APPROVAL_DELIVERY_HANDOFF_STATUSES = {
    "not_required",
    "ready_for_handoff",
    "handoff_attempted",
    "delivered_for_review",
    "handoff_blocked",
    "handoff_failed",
    "insufficient_truth",
}

APPROVAL_DELIVERY_HANDOFF_VALIDITIES = {
    "valid",
    "partial",
    "malformed",
    "insufficient_truth",
}

APPROVAL_DELIVERY_HANDOFF_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}

DELIVERY_MODES = {
    "gmail_draft",
    "gmail_send",
    "review_queue_only",
    "not_applicable",
    "unknown",
}

DELIVERY_OUTCOMES = {
    "not_attempted",
    "draft_created",
    "sent",
    "queued_for_review",
    "skipped",
    "blocked",
    "failed",
    "unknown",
}

DOWNSTREAM_ADAPTERS = {
    "internal_automation",
    "none",
    "unknown",
}

APPROVAL_DELIVERY_HANDOFF_REASON_CODES = {
    "malformed_handoff_inputs",
    "insufficient_handoff_truth",
    "approval_not_required",
    "adapter_missing_for_required_mode",
    "handoff_policy_blocked",
    "handoff_failed",
    "handoff_succeeded",
    "review_queue_handoff_succeeded",
    "unknown_handoff_posture",
    "alias_deduplicated",
    "no_reason",
}

APPROVAL_DELIVERY_HANDOFF_REASON_ORDER = (
    "malformed_handoff_inputs",
    "insufficient_handoff_truth",
    "approval_not_required",
    "adapter_missing_for_required_mode",
    "handoff_policy_blocked",
    "handoff_failed",
    "handoff_succeeded",
    "review_queue_handoff_succeeded",
    "unknown_handoff_posture",
    "alias_deduplicated",
    "no_reason",
)

_ALLOWED_SUPPORTING_REFS = (
    "approval_email_delivery_contract.approval_email_status",
    "approval_email_delivery_contract.approval_required",
    "approval_email_delivery_contract.delivery_mode",
    "approval_runtime_rules_contract.runtime_rules_version",
    "fleet_safety_control_contract.fleet_safety_status",
    "fleet_safety_control_contract.fleet_restart_decision",
    "failure_bucketing_hardening_contract.primary_failure_bucket",
    "failure_bucketing_hardening_contract.bucket_severity",
    "lane_stabilization_contract.current_lane",
)

APPROVAL_DELIVERY_HANDOFF_RUN_STATE_SUMMARY_SAFE_FIELDS = (
    "approval_delivery_handoff_present",
)

APPROVAL_DELIVERY_HANDOFF_SUMMARY_SAFE_FIELDS = (
    "approval_delivery_handoff_status",
    "approval_delivery_handoff_validity",
    "approval_delivery_handoff_confidence",
    "delivery_mode",
    "delivery_outcome",
    "approval_pending_human_response",
    "approval_delivery_handoff_primary_reason",
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
    normalized = [
        value
        for value in _ordered_unique(values)
        if value in APPROVAL_DELIVERY_HANDOFF_REASON_CODES
    ]
    ordered: list[str] = []
    for code in APPROVAL_DELIVERY_HANDOFF_REASON_ORDER:
        if code in normalized:
            ordered.append(code)
    return ordered


def _normalize_supporting_refs(values: list[str]) -> list[str]:
    allowed = set(_ALLOWED_SUPPORTING_REFS)
    return [value for value in _ordered_unique(values) if value in allowed]


def _coerce_mapping(value: Any) -> tuple[dict[str, Any], bool]:
    if isinstance(value, Mapping):
        return dict(value), False
    return {}, value is not None


def _load_handoff_adapter_from_env() -> Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None:
    target = _normalize_text(
        os.getenv("INTERNAL_AUTOMATION_APPROVAL_DELIVERY_ADAPTER"),
        default=_normalize_text(os.getenv("INTERNAL_AUTOMATION_APPROVAL_EMAIL_ADAPTER"), default=""),
    )
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
    if callable(candidate):
        return candidate
    return None


def _invoke_handoff_adapter(
    *,
    delivery_mode: str,
    request_payload: Mapping[str, Any],
    adapter: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None,
) -> dict[str, Any]:
    if delivery_mode == "review_queue_only":
        return {
            "delivery_attempted": True,
            "delivery_outcome": "queued_for_review",
            "downstream_adapter": "none",
            "downstream_delivery_id": _normalize_text(request_payload.get("run_id"), default=""),
            "downstream_thread_id": "",
            "downstream_message_id": "",
            "downstream_delivery_timestamp": "",
            "adapter_reason": "review_queue_only_mode",
        }

    resolved_adapter = adapter or _load_handoff_adapter_from_env()
    if resolved_adapter is None:
        return {
            "delivery_attempted": False,
            "delivery_outcome": "blocked",
            "downstream_adapter": "none",
            "downstream_delivery_id": "",
            "downstream_thread_id": "",
            "downstream_message_id": "",
            "downstream_delivery_timestamp": "",
            "adapter_reason": "adapter_unavailable",
        }

    try:
        raw = resolved_adapter(dict(request_payload))
    except Exception as exc:
        return {
            "delivery_attempted": True,
            "delivery_outcome": "failed",
            "downstream_adapter": "internal_automation",
            "downstream_delivery_id": "",
            "downstream_thread_id": "",
            "downstream_message_id": "",
            "downstream_delivery_timestamp": "",
            "adapter_reason": _normalize_text(str(exc), default="adapter_error"),
        }

    payload = dict(raw) if isinstance(raw, Mapping) else {}
    outcome = _normalize_enum(
        payload.get("delivery_outcome"),
        allowed=DELIVERY_OUTCOMES,
        default="unknown",
    )
    adapter_status = _normalize_text(payload.get("status"), default="")
    if outcome == "unknown":
        mapped = {
            "sent": "sent",
            "draft_created": "draft_created",
            "queued_for_review": "queued_for_review",
            "blocked": "blocked",
            "failed": "failed",
            "skipped": "skipped",
        }
        outcome = mapped.get(adapter_status, "unknown")

    attempted = _normalize_bool(payload.get("delivery_attempted"))
    if outcome in {"draft_created", "sent", "failed", "queued_for_review"}:
        attempted = True
    elif outcome in {"blocked", "skipped", "not_attempted"} and "delivery_attempted" not in payload:
        attempted = False

    return {
        "delivery_attempted": attempted,
        "delivery_outcome": outcome,
        "downstream_adapter": _normalize_enum(
            payload.get("downstream_adapter"),
            allowed=DOWNSTREAM_ADAPTERS,
            default="internal_automation",
        ),
        "downstream_delivery_id": _normalize_text(
            payload.get("downstream_delivery_id") or payload.get("delivery_id"),
            default="",
        ),
        "downstream_thread_id": _normalize_text(
            payload.get("downstream_thread_id") or payload.get("thread_id"),
            default="",
        ),
        "downstream_message_id": _normalize_text(
            payload.get("downstream_message_id") or payload.get("message_id"),
            default="",
        ),
        "downstream_delivery_timestamp": _normalize_text(
            payload.get("downstream_delivery_timestamp")
            or payload.get("delivery_timestamp")
            or payload.get("timestamp"),
            default="",
        ),
        "adapter_reason": _normalize_text(
            payload.get("adapter_reason") or payload.get("message"),
            default="",
        ),
    }


def build_approval_delivery_handoff_contract_surface(
    *,
    run_id: str,
    objective_contract_payload: Mapping[str, Any] | None,
    approval_email_delivery_payload: Mapping[str, Any] | None,
    approval_runtime_rules_payload: Mapping[str, Any] | None,
    fleet_safety_control_payload: Mapping[str, Any] | None,
    failure_bucketing_hardening_payload: Mapping[str, Any] | None,
    lane_stabilization_contract_payload: Mapping[str, Any] | None,
    run_state_payload: Mapping[str, Any] | None,
    contract_artifact_index_payload: Mapping[str, Any] | None = None,
    handoff_adapter: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    objective, objective_malformed = _coerce_mapping(objective_contract_payload)
    approval_email, approval_email_malformed = _coerce_mapping(approval_email_delivery_payload)
    runtime_rules, runtime_rules_malformed = _coerce_mapping(approval_runtime_rules_payload)
    fleet, fleet_malformed = _coerce_mapping(fleet_safety_control_payload)
    hard_bucket, hard_bucket_malformed = _coerce_mapping(failure_bucketing_hardening_payload)
    lane, lane_malformed = _coerce_mapping(lane_stabilization_contract_payload)
    run_state, run_state_malformed = _coerce_mapping(run_state_payload)
    artifact_index, artifact_index_malformed = _coerce_mapping(contract_artifact_index_payload)

    malformed_inputs = any(
        (
            objective_malformed,
            approval_email_malformed,
            runtime_rules_malformed,
            fleet_malformed,
            hard_bucket_malformed,
            lane_malformed,
            run_state_malformed,
            artifact_index_malformed,
        )
    )

    objective_id = _normalize_text(
        objective.get("objective_id") or approval_email.get("objective_id"),
        default="",
    )
    approval_email_status = _normalize_text(
        approval_email.get("approval_email_status"),
        default="",
    )
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
    recipient_target = _normalize_text(approval_email.get("recipient_target"), default="")
    approval_subject = _normalize_text(approval_email.get("approval_subject"), default="")
    approval_option_set = _normalize_text(
        approval_email.get("approval_option_set"),
        default="unknown",
    )
    approval_summary_compact = _normalize_text(
        approval_email.get("approval_summary_compact"),
        default="",
    )
    approval_body_compact = _normalize_text(
        approval_email.get("approval_body_compact"),
        default="",
    )
    allowed_reply_commands = [
        _normalize_text(item, default="")
        for item in (approval_email.get("allowed_reply_commands") or [])
        if _normalize_text(item, default="")
    ]
    delivery_mode = _normalize_enum(
        approval_email.get("delivery_mode"),
        allowed=DELIVERY_MODES,
        default="unknown",
    )

    runtime_rules_present = bool(
        _normalize_text(runtime_rules.get("runtime_rules_version"), default="")
    ) or _normalize_bool(run_state.get("approval_runtime_rules_present"))
    approval_email_delivery_present = bool(approval_email_status) or _normalize_bool(
        run_state.get("approval_email_delivery_present")
    )

    insufficient_truth = any(
        (
            approval_email_status in {"", "insufficient_truth"},
            approval_required and delivery_mode in {"unknown", "not_applicable"},
            approval_required and not recipient_target,
            approval_required and not approval_subject,
            approval_required and not approval_body_compact,
        )
    )

    delivery_attempted = False
    delivery_outcome = "not_attempted"
    delivery_blocked = False
    delivery_failed = False
    delivery_succeeded = False
    downstream_adapter = "none"
    downstream_delivery_id = ""
    downstream_thread_id = ""
    downstream_message_id = ""
    downstream_delivery_timestamp = ""
    adapter_reason = ""

    lead_reason = "unknown_handoff_posture"
    status = "ready_for_handoff"
    validity = "valid"
    confidence = "medium"

    if malformed_inputs:
        lead_reason = "malformed_handoff_inputs"
        status = "insufficient_truth"
        validity = "malformed"
        confidence = "low"
    elif insufficient_truth:
        lead_reason = "insufficient_handoff_truth"
        status = "insufficient_truth"
        validity = "insufficient_truth"
        confidence = "low"
    elif not approval_required:
        lead_reason = "approval_not_required"
        status = "not_required"
        validity = "valid"
        confidence = "high"
        delivery_mode = "not_applicable"
        delivery_outcome = "skipped"
    else:
        request_payload = {
            "run_id": _normalize_text(run_id, default=""),
            "objective_id": objective_id,
            "recipient_target": recipient_target,
            "delivery_mode": delivery_mode,
            "approval_subject": approval_subject,
            "approval_body_compact": approval_body_compact,
            "approval_option_set": approval_option_set,
            "approval_summary_compact": approval_summary_compact,
            "allowed_reply_commands": allowed_reply_commands,
            "proposed_next_direction": proposed_next_direction,
            "proposed_target_lane": proposed_target_lane,
            "proposed_restart_mode": proposed_restart_mode,
        }
        result = _invoke_handoff_adapter(
            delivery_mode=delivery_mode,
            request_payload=request_payload,
            adapter=handoff_adapter,
        )
        delivery_attempted = _normalize_bool(result.get("delivery_attempted"))
        delivery_outcome = _normalize_enum(
            result.get("delivery_outcome"),
            allowed=DELIVERY_OUTCOMES,
            default="unknown",
        )
        downstream_adapter = _normalize_enum(
            result.get("downstream_adapter"),
            allowed=DOWNSTREAM_ADAPTERS,
            default="unknown",
        )
        downstream_delivery_id = _normalize_text(result.get("downstream_delivery_id"), default="")
        downstream_thread_id = _normalize_text(result.get("downstream_thread_id"), default="")
        downstream_message_id = _normalize_text(result.get("downstream_message_id"), default="")
        downstream_delivery_timestamp = _normalize_text(
            result.get("downstream_delivery_timestamp"),
            default="",
        )
        adapter_reason = _normalize_text(result.get("adapter_reason"), default="")

        delivery_succeeded = delivery_outcome in {
            "draft_created",
            "sent",
            "queued_for_review",
        }
        delivery_blocked = delivery_outcome == "blocked"
        delivery_failed = delivery_outcome == "failed"

        if delivery_blocked and adapter_reason == "adapter_unavailable":
            lead_reason = "adapter_missing_for_required_mode"
            status = "handoff_blocked"
            validity = "partial"
            confidence = "medium"
        elif delivery_blocked:
            lead_reason = "handoff_policy_blocked"
            status = "handoff_blocked"
            validity = "partial"
            confidence = "medium"
        elif delivery_failed:
            lead_reason = "handoff_failed"
            status = "handoff_failed"
            validity = "partial"
            confidence = "low"
        elif delivery_succeeded:
            if delivery_mode == "review_queue_only":
                lead_reason = "review_queue_handoff_succeeded"
            else:
                lead_reason = "handoff_succeeded"
            status = "delivered_for_review"
            validity = "valid"
            confidence = "high"
        elif delivery_attempted:
            lead_reason = "unknown_handoff_posture"
            status = "handoff_attempted"
            validity = "partial"
            confidence = "low"
        else:
            lead_reason = "unknown_handoff_posture"
            status = "ready_for_handoff"
            validity = "partial"
            confidence = "low"

    approval_pending_human_response = bool(approval_required and delivery_succeeded)
    restart_blocked_pending_approval = _normalize_bool(
        approval_email.get("restart_blocked_pending_approval")
    )
    restart_held_pending_approval = _normalize_bool(
        approval_email.get("restart_held_pending_approval")
    )
    approval_can_clear_restart_block = _normalize_bool(
        approval_email.get("approval_can_clear_restart_block")
    )

    alias_deduplicated = _normalize_bool(
        approval_email.get("alias_deduplicated")
    ) or _normalize_bool(
        run_state.get("retention_alias_deduplicated")
    )
    reason_codes = _normalize_reason_codes(
        [
            lead_reason,
            "alias_deduplicated" if alias_deduplicated else "",
        ]
    )
    if not reason_codes:
        reason_codes = ["no_reason"]

    supporting_refs = _normalize_supporting_refs(
        [
            "approval_email_delivery_contract.approval_email_status"
            if approval_email_status
            else "",
            "approval_email_delivery_contract.approval_required"
            if "approval_required" in approval_email
            else "",
            "approval_email_delivery_contract.delivery_mode"
            if "delivery_mode" in approval_email
            else "",
            "approval_runtime_rules_contract.runtime_rules_version"
            if runtime_rules_present
            else "",
            "fleet_safety_control_contract.fleet_safety_status"
            if _normalize_text(fleet.get("fleet_safety_status"), default="")
            else "",
            "fleet_safety_control_contract.fleet_restart_decision"
            if _normalize_text(fleet.get("fleet_restart_decision"), default="")
            else "",
            "failure_bucketing_hardening_contract.primary_failure_bucket"
            if _normalize_text(hard_bucket.get("primary_failure_bucket"), default="")
            else "",
            "failure_bucketing_hardening_contract.bucket_severity"
            if _normalize_text(hard_bucket.get("bucket_severity"), default="")
            else "",
            "lane_stabilization_contract.current_lane"
            if _normalize_text(lane.get("current_lane"), default="")
            else "",
        ]
    )

    return {
        "schema_version": APPROVAL_DELIVERY_HANDOFF_SCHEMA_VERSION,
        "run_id": _normalize_text(run_id, default=""),
        "objective_id": objective_id,
        "approval_delivery_handoff_status": _normalize_enum(
            status,
            allowed=APPROVAL_DELIVERY_HANDOFF_STATUSES,
            default="insufficient_truth",
        ),
        "approval_delivery_handoff_validity": _normalize_enum(
            validity,
            allowed=APPROVAL_DELIVERY_HANDOFF_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_delivery_handoff_confidence": _normalize_enum(
            confidence,
            allowed=APPROVAL_DELIVERY_HANDOFF_CONFIDENCE_LEVELS,
            default="low",
        ),
        "delivery_mode": _normalize_enum(
            delivery_mode,
            allowed=DELIVERY_MODES,
            default="unknown",
        ),
        "delivery_attempted": bool(delivery_attempted),
        "delivery_outcome": _normalize_enum(
            delivery_outcome,
            allowed=DELIVERY_OUTCOMES,
            default="unknown",
        ),
        "delivery_blocked": bool(delivery_blocked),
        "delivery_failed": bool(delivery_failed),
        "delivery_succeeded": bool(delivery_succeeded),
        "downstream_adapter": _normalize_enum(
            downstream_adapter,
            allowed=DOWNSTREAM_ADAPTERS,
            default="unknown",
        ),
        "downstream_delivery_id": downstream_delivery_id,
        "downstream_thread_id": downstream_thread_id,
        "downstream_message_id": downstream_message_id,
        "downstream_delivery_timestamp": downstream_delivery_timestamp,
        "approval_pending_human_response": bool(approval_pending_human_response),
        "restart_blocked_pending_approval": bool(restart_blocked_pending_approval),
        "restart_held_pending_approval": bool(restart_held_pending_approval),
        "approval_can_clear_restart_block": bool(approval_can_clear_restart_block),
        "recipient_target": recipient_target,
        "approval_subject": approval_subject,
        "approval_option_set": approval_option_set,
        "approval_summary_compact": approval_summary_compact,
        "approval_delivery_handoff_primary_reason": reason_codes[0],
        "approval_delivery_handoff_reason_codes": reason_codes,
        "approval_email_status": approval_email_status or "insufficient_truth",
        "approval_required": bool(approval_required),
        "approval_priority": approval_priority,
        "proposed_next_direction": proposed_next_direction,
        "proposed_target_lane": proposed_target_lane,
        "proposed_restart_mode": proposed_restart_mode,
        "approval_email_delivery_present": bool(approval_email_delivery_present),
        "runtime_rules_present": bool(runtime_rules_present),
        "fleet_safety_status": _normalize_text(
            fleet.get("fleet_safety_status"),
            default="insufficient_truth",
        ),
        "fleet_restart_decision": _normalize_text(
            fleet.get("fleet_restart_decision"),
            default="unknown",
        ),
        "primary_failure_bucket": _normalize_text(
            hard_bucket.get("primary_failure_bucket"),
            default="unknown",
        ),
        "bucket_severity": _normalize_text(
            hard_bucket.get("bucket_severity"),
            default="unknown",
        ),
        "current_lane": _normalize_text(
            lane.get("current_lane"),
            default="unknown",
        ),
        "supporting_compact_truth_refs": supporting_refs,
        "next_safe_hint": _normalize_text(run_state.get("next_safe_action"), default=""),
        "closure_followup_hint": _normalize_text(
            run_state.get("closure_followup_hint"),
            default="",
        ),
        "retry_hint": _normalize_text(run_state.get("retry_hint"), default=""),
        "reentry_hint": _normalize_text(run_state.get("reentry_hint"), default=""),
        "delivery_adapter_reason": adapter_reason,
        "artifact_index_present": bool(artifact_index),
    }


def build_approval_delivery_handoff_run_state_summary_surface(
    approval_delivery_handoff_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_delivery_handoff_payload or {})
    return {
        "approval_delivery_handoff_present": bool(
            _normalize_text(payload.get("approval_delivery_handoff_status"), default="")
        )
        or _normalize_bool(payload.get("approval_delivery_handoff_present"))
    }


def build_approval_delivery_handoff_summary_surface(
    approval_delivery_handoff_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = dict(approval_delivery_handoff_payload or {})
    return {
        "approval_delivery_handoff_status": _normalize_enum(
            payload.get("approval_delivery_handoff_status"),
            allowed=APPROVAL_DELIVERY_HANDOFF_STATUSES,
            default="insufficient_truth",
        ),
        "approval_delivery_handoff_validity": _normalize_enum(
            payload.get("approval_delivery_handoff_validity"),
            allowed=APPROVAL_DELIVERY_HANDOFF_VALIDITIES,
            default="insufficient_truth",
        ),
        "approval_delivery_handoff_confidence": _normalize_enum(
            payload.get("approval_delivery_handoff_confidence"),
            allowed=APPROVAL_DELIVERY_HANDOFF_CONFIDENCE_LEVELS,
            default="low",
        ),
        "delivery_mode": _normalize_enum(
            payload.get("delivery_mode"),
            allowed=DELIVERY_MODES,
            default="unknown",
        ),
        "delivery_outcome": _normalize_enum(
            payload.get("delivery_outcome"),
            allowed=DELIVERY_OUTCOMES,
            default="unknown",
        ),
        "approval_pending_human_response": _normalize_bool(
            payload.get("approval_pending_human_response")
        ),
        "approval_delivery_handoff_primary_reason": _normalize_text(
            payload.get("approval_delivery_handoff_primary_reason"),
            default="no_reason",
        )
        if _normalize_text(
            payload.get("approval_delivery_handoff_primary_reason"),
            default="",
        )
        in APPROVAL_DELIVERY_HANDOFF_REASON_CODES
        else "no_reason",
    }

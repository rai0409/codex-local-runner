from __future__ import annotations

from typing import Any


APPROVAL_ACTOR_CLASSES = (
    "self",
    "operator",
    "reviewer",
    "approver",
    "admin",
    "unknown",
)

_APPROVAL_ACTOR_SET = set(APPROVAL_ACTOR_CLASSES)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).lower()


def normalize_actor_class(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized if normalized in _APPROVAL_ACTOR_SET else "unknown"


def derive_expected_actor_class(
    *,
    recipient_class: Any | None = None,
    approval_required: Any | None = None,
    manual_review_required: Any | None = None,
    fleet_safety_status: Any | None = None,
    proposed_target_lane: Any | None = None,
) -> str:
    recipient = normalize_actor_class(recipient_class)
    if recipient != "unknown":
        return recipient

    manual_required = bool(manual_review_required)
    safety_status = _normalize_text(fleet_safety_status)
    target_lane = _normalize_text(proposed_target_lane)

    if manual_required or target_lane == "manual_review_preparation":
        return "reviewer"
    if safety_status in {"stop", "freeze"}:
        return "approver"
    if bool(approval_required):
        return "operator"
    if approval_required is False:
        return "self"
    return "unknown"


def derive_approval_actor_policy(
    *,
    recipient_class: Any | None = None,
    approval_required: Any | None = None,
    manual_review_required: Any | None = None,
    fleet_safety_status: Any | None = None,
    proposed_target_lane: Any | None = None,
) -> dict[str, Any]:
    expected = derive_expected_actor_class(
        recipient_class=recipient_class,
        approval_required=approval_required,
        manual_review_required=manual_review_required,
        fleet_safety_status=fleet_safety_status,
        proposed_target_lane=proposed_target_lane,
    )

    if expected == "unknown":
        if bool(approval_required) or bool(manual_review_required):
            fallback = "operator"
            confidence = "low"
        elif approval_required is False:
            fallback = "self"
            confidence = "medium"
        else:
            fallback = "operator"
            confidence = "low"
        decision = "fallback"
    else:
        fallback = expected
        confidence = "high"
        decision = "resolved"

    return {
        "actor_class": expected,
        "fallback_actor_class": fallback,
        "actor_decision": decision,
        "actor_confidence": confidence,
    }


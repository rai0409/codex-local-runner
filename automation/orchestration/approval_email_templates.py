from __future__ import annotations

from typing import Any
from typing import Mapping


APPROVAL_OPTION_SETS = {
    "approve_or_reject",
    "approve_replan_or_reject",
    "approve_restart_hold_or_reject",
    "approve_manual_only",
    "unknown",
}

APPROVAL_SUBJECT_MAX_LENGTH = 140
APPROVAL_BODY_MAX_LENGTH = 480
APPROVAL_SUMMARY_MAX_LENGTH = 160

OPTIONAL_HINT_ORDER = (
    "next_safe_hint",
    "closure_followup_hint",
    "retry_hint",
    "reentry_hint",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def normalize_compact_token(value: Any, *, default: str = "unknown") -> str:
    text = _normalize_text(value, default=default)
    return " ".join(text.split())


def truncate_compact_text(text: str, *, max_length: int) -> str:
    normalized = _normalize_text(text, default="")
    if max_length <= 0:
        return ""
    if len(normalized) <= max_length:
        return normalized
    if max_length <= 3:
        return normalized[:max_length]
    return normalized[: max_length - 3].rstrip() + "..."


def render_approval_subject(
    *,
    priority: str,
    run_id: str,
    primary_failure_bucket: str,
    proposed_next_direction: str,
) -> str:
    subject = (
        f"[Approval Needed][{normalize_compact_token(priority)}] run "
        f"{normalize_compact_token(run_id, default='unknown')}: "
        f"{normalize_compact_token(primary_failure_bucket)} -> "
        f"{normalize_compact_token(proposed_next_direction)}"
    )
    return truncate_compact_text(subject, max_length=APPROVAL_SUBJECT_MAX_LENGTH)


def render_approval_summary_compact(
    *,
    primary_reason: str,
    proposed_direction: str,
    restart_mode: str,
    priority: str,
) -> str:
    summary = (
        f"reason={normalize_compact_token(primary_reason)};"
        f"direction={normalize_compact_token(proposed_direction)};"
        f"restart={normalize_compact_token(restart_mode)};"
        f"priority={normalize_compact_token(priority)}"
    )
    return truncate_compact_text(summary, max_length=APPROVAL_SUMMARY_MAX_LENGTH)


def render_approval_body_compact(
    *,
    run_id: str,
    fleet_safety_status: str,
    primary_reason: str,
    proposed_direction: str,
    restart_mode: str,
    allowed_reply_commands: tuple[str, ...],
    hints: Mapping[str, Any] | None = None,
) -> str:
    hint_payload = dict(hints or {})
    lines = [
        f"Run: {normalize_compact_token(run_id, default='unknown')}",
        f"Safety: {normalize_compact_token(fleet_safety_status)}",
        f"Reason: {normalize_compact_token(primary_reason)}",
        f"Direction: {normalize_compact_token(proposed_direction)}",
        f"Restart: {normalize_compact_token(restart_mode)}",
        "Reply: " + " | ".join([normalize_compact_token(v) for v in allowed_reply_commands]),
    ]

    for key in OPTIONAL_HINT_ORDER:
        hint_value = normalize_compact_token(hint_payload.get(key), default="")
        if not hint_value:
            continue
        lines.append(f"Hint: {hint_value}")
        break

    body = "\n".join(lines)
    return truncate_compact_text(body, max_length=APPROVAL_BODY_MAX_LENGTH)


def derive_approval_option_set(
    *,
    proposed_direction: str,
    restart_blocked: bool,
    restart_hold: bool,
    manual_only_terminal: bool,
) -> str:
    if manual_only_terminal or proposed_direction in {"manual_review_preparation", "stop_no_restart", "unknown"}:
        return "approve_manual_only"
    if proposed_direction == "replan_preparation":
        return "approve_replan_or_reject"
    if restart_blocked or restart_hold:
        return "approve_restart_hold_or_reject"
    if proposed_direction in {
        "same_lane_retry",
        "repair_retry",
        "truth_gathering",
        "closure_followup",
    }:
        return "approve_or_reject"
    return "unknown"

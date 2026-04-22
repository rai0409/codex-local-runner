from __future__ import annotations

from typing import Any


ALLOWED_REPLY_COMMANDS = (
    "OK RETRY",
    "OK REPLAN",
    "OK TRUTH",
    "OK CLOSE",
    "HOLD",
    "REJECT",
)

APPROVAL_REPLY_COMMANDS_SET = set(ALLOWED_REPLY_COMMANDS)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def normalize_reply_command(command: Any) -> str:
    text = _normalize_text(command, default="")
    if not text:
        return ""
    return " ".join(text.upper().split())


def is_supported_reply_command(command: Any) -> bool:
    return normalize_reply_command(command) in APPROVAL_REPLY_COMMANDS_SET


def parse_reply_command(command: Any) -> dict[str, Any]:
    normalized = normalize_reply_command(command)
    return {
        "raw": _normalize_text(command, default=""),
        "normalized": normalized,
        "supported": normalized in APPROVAL_REPLY_COMMANDS_SET,
    }


def allowed_reply_commands_for_direction(proposed_next_direction: str) -> tuple[str, ...]:
    direction = _normalize_text(proposed_next_direction, default="unknown")
    if direction in {"same_lane_retry", "repair_retry"}:
        return ("OK RETRY", "HOLD", "REJECT")
    if direction == "replan_preparation":
        return ("OK REPLAN", "HOLD", "REJECT")
    if direction == "truth_gathering":
        return ("OK TRUTH", "HOLD", "REJECT")
    if direction == "closure_followup":
        return ("OK CLOSE", "HOLD", "REJECT")
    return ("HOLD", "REJECT")


def map_approved_reply_command(command: Any) -> dict[str, Any]:
    normalized = normalize_reply_command(command)
    if normalized == "OK RETRY":
        return {
            "command": normalized,
            "supported": True,
            "approval_decision": "approved",
            "proposed_next_direction": "same_lane_retry",
            "proposed_target_lane": "bounded_local_patch",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_restart",
            "restart_allowed": True,
        }
    if normalized == "OK REPLAN":
        return {
            "command": normalized,
            "supported": True,
            "approval_decision": "approved",
            "proposed_next_direction": "replan_preparation",
            "proposed_target_lane": "replan_preparation",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_replan",
            "restart_allowed": True,
        }
    if normalized == "OK TRUTH":
        return {
            "command": normalized,
            "supported": True,
            "approval_decision": "approved",
            "proposed_next_direction": "truth_gathering",
            "proposed_target_lane": "truth_gathering",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_recollect",
            "restart_allowed": True,
        }
    if normalized == "OK CLOSE":
        return {
            "command": normalized,
            "supported": True,
            "approval_decision": "approved",
            "proposed_next_direction": "closure_followup",
            "proposed_target_lane": "closure_followup",
            "proposed_restart_mode": "approval_required_then_restart",
            "proposed_action_class": "review_and_close_followup",
            "restart_allowed": True,
        }
    if normalized == "HOLD":
        return {
            "command": normalized,
            "supported": True,
            "approval_decision": "held",
            "proposed_next_direction": "unknown",
            "proposed_target_lane": "unknown",
            "proposed_restart_mode": "held",
            "proposed_action_class": "review_only",
            "restart_allowed": False,
        }
    if normalized == "REJECT":
        return {
            "command": normalized,
            "supported": True,
            "approval_decision": "rejected",
            "proposed_next_direction": "stop_no_restart",
            "proposed_target_lane": "unknown",
            "proposed_restart_mode": "blocked",
            "proposed_action_class": "stop_only",
            "restart_allowed": False,
        }
    return {
        "command": normalized,
        "supported": False,
        "approval_decision": "unknown",
        "proposed_next_direction": "unknown",
        "proposed_target_lane": "unknown",
        "proposed_restart_mode": "unknown",
        "proposed_action_class": "unknown",
        "restart_allowed": False,
    }

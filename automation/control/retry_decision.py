from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Callable
from typing import Mapping

from automation.control.retry_context import normalize_retry_context
from automation.control.retry_policy import DECISION_ESCALATE_TO_HUMAN
from automation.control.retry_policy import DECISION_PAUSE_AND_WAIT
from automation.control.retry_policy import DECISION_RETRY_NOW
from automation.control.retry_policy import DECISION_TERMINAL_REFUSAL
from automation.control.retry_policy import load_retry_policy
from automation.control.retry_policy import normalize_retry_policy
from automation.control.retry_policy import resolve_retry_policy_entry
from automation.scheduler.pause_state import PAUSE_STATE_CHECKS
from automation.scheduler.pause_state import PAUSE_STATE_HUMAN
from automation.scheduler.pause_state import PAUSE_STATE_OTHER
from automation.scheduler.pause_state import PAUSE_STATE_PROVIDER_CAPACITY
from automation.scheduler.pause_state import PAUSE_STATE_RATE_LIMIT
from automation.scheduler.pause_state import is_pause_active
from automation.scheduler.pause_state import is_pause_resume_eligible

_RETRY_CLASSES = {
    "same_prompt_retry",
    "repair_prompt_retry",
    "signal_recollect",
}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip().lower()
    return text if text else default


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _as_non_negative_int(value: Any, *, default: int) -> int:
    parsed = _as_optional_int(value)
    if parsed is None:
        return default
    return max(0, parsed)


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def normalize_provider_class(provider_name: str | None = None, provider_class: str | None = None) -> str:
    if provider_class:
        normalized = _normalize_text(provider_class, default="generic")
        if normalized:
            return normalized
    normalized_name = _normalize_text(provider_name, default="")
    if normalized_name in {"codex", "chatgpt", "github"}:
        return normalized_name
    if normalized_name.startswith("codex"):
        return "codex"
    if normalized_name.startswith("chatgpt"):
        return "chatgpt"
    if normalized_name.startswith("github"):
        return "github"
    return "generic"


def _resolve_failure_type(
    *,
    explicit_failure_type: str | None,
    structured_result: Mapping[str, Any] | None,
    retry_after_seconds: int | None,
    pause_state_payload: Mapping[str, Any] | None,
    next_action: str | None,
    reason: str | None,
) -> tuple[str, str]:
    direct = _normalize_text(explicit_failure_type, default="")
    if direct:
        return direct, "explicit_failure_type"

    result_payload = structured_result if isinstance(structured_result, Mapping) else {}
    result_failure = _normalize_text(result_payload.get("failure_type"), default="")
    if result_failure:
        return result_failure, "structured_result.failure_type"

    execution = _as_mapping(result_payload.get("execution")) or {}
    execution_failure = _normalize_text(execution.get("failure_type"), default="")
    if execution_failure:
        return execution_failure, "structured_result.execution.failure_type"

    if retry_after_seconds is not None and retry_after_seconds >= 0:
        return "provider_rate_limited", "retry_after_seconds"

    if is_pause_active(pause_state_payload):
        pause_state = _normalize_text((pause_state_payload or {}).get("pause_state"), default="")
        if pause_state == PAUSE_STATE_PROVIDER_CAPACITY:
            return "provider_usage_exhausted", "pause_state"
        if pause_state == PAUSE_STATE_RATE_LIMIT:
            return "provider_rate_limited", "pause_state"
        if pause_state == PAUSE_STATE_CHECKS:
            return "check_pending", "pause_state"
        if pause_state == PAUSE_STATE_HUMAN:
            return "human_required", "pause_state"

    action = _normalize_text(next_action, default="")
    if action == "wait_for_checks":
        return "check_pending", "next_action"

    reason_text = _normalize_text(reason, default="")
    if any(token in reason_text for token in ("rate limit", "retry-after", "too many requests", "429")):
        return "provider_rate_limited", "reason"
    if any(token in reason_text for token in ("capacity unavailable", "capacity exhausted", "provider capacity")):
        return "provider_usage_exhausted", "reason"
    if "auth" in reason_text or "permission denied" in reason_text or "forbidden" in reason_text:
        return "auth_failure", "reason"
    if "timeout" in reason_text:
        return "transport_timeout", "reason"

    return "unknown_failure", "fallback"


def _fallback_decision(
    *,
    failure_type: str,
    next_action: str | None,
    retry_after_seconds: int | None,
) -> dict[str, Any]:
    if failure_type in {"provider_usage_exhausted", "provider_capacity_exhausted", "provider_unavailable"}:
        return {
            "decision_kind": DECISION_PAUSE_AND_WAIT,
            "max_attempts": 0,
            "backoff_seconds": (300,),
            "pause_state": PAUSE_STATE_PROVIDER_CAPACITY,
            "human_required": False,
            "retry_class": None,
            "id": "fallback_provider_capacity",
        }
    if failure_type in {"provider_rate_limited"}:
        return {
            "decision_kind": DECISION_PAUSE_AND_WAIT,
            "max_attempts": 0,
            "backoff_seconds": (max(30, retry_after_seconds or 60),),
            "pause_state": PAUSE_STATE_RATE_LIMIT,
            "human_required": False,
            "retry_class": None,
            "id": "fallback_rate_limit",
        }
    if failure_type in {"check_pending"}:
        return {
            "decision_kind": DECISION_PAUSE_AND_WAIT,
            "max_attempts": 0,
            "backoff_seconds": (120,),
            "pause_state": PAUSE_STATE_CHECKS,
            "human_required": False,
            "retry_class": None,
            "id": "fallback_checks_pending",
        }
    if failure_type in {"auth_failure", "permission_denied", "forbidden"}:
        return {
            "decision_kind": DECISION_TERMINAL_REFUSAL,
            "max_attempts": 0,
            "backoff_seconds": (0,),
            "pause_state": None,
            "human_required": True,
            "retry_class": None,
            "id": "fallback_auth_failure",
        }
    if failure_type in {"transport_timeout", "execution_failure", "evaluation_failure"}:
        return {
            "decision_kind": DECISION_RETRY_NOW,
            "max_attempts": 1,
            "backoff_seconds": (30,),
            "pause_state": None,
            "human_required": False,
            "retry_class": "same_prompt_retry",
            "id": "fallback_retry_once",
        }
    action = _normalize_text(next_action, default="")
    if action in _RETRY_CLASSES:
        return {
            "decision_kind": DECISION_RETRY_NOW,
            "max_attempts": 1,
            "backoff_seconds": (0,),
            "pause_state": None,
            "human_required": False,
            "retry_class": action,
            "id": "fallback_explicit_retry_action",
        }
    return {
        "decision_kind": DECISION_ESCALATE_TO_HUMAN,
        "max_attempts": 0,
        "backoff_seconds": (0,),
        "pause_state": PAUSE_STATE_OTHER,
        "human_required": True,
        "retry_class": None,
        "id": "fallback_escalate",
    }


def _compute_remaining_attempts(
    *,
    retry_context: Mapping[str, Any],
    max_attempts: int,
    retry_class: str | None,
) -> int:
    budget_remaining = _as_non_negative_int(retry_context.get("retry_budget_remaining"), default=0)
    if max_attempts <= 0:
        return 0
    normalized_retry_class = _normalize_text(retry_class, default="")
    prior_retry_class = _normalize_text(retry_context.get("prior_retry_class"), default="")
    prior_attempt_count = _as_non_negative_int(retry_context.get("prior_attempt_count"), default=0)
    consumed = prior_attempt_count if normalized_retry_class and prior_retry_class == normalized_retry_class else 0
    by_attempts = max(0, max_attempts - consumed)
    return min(by_attempts, budget_remaining)


def _resolve_retry_class(
    *,
    explicit_retry_class: str | None,
    next_action: str | None,
    policy_retry_class: str | None,
) -> str | None:
    explicit = _normalize_text(explicit_retry_class, default="")
    if explicit:
        return explicit
    action = _normalize_text(next_action, default="")
    if action in _RETRY_CLASSES:
        return action
    policy_value = _normalize_text(policy_retry_class, default="")
    return policy_value or None


def evaluate_retry_decision(
    *,
    provider_name: str | None = None,
    provider_class: str | None = None,
    operation_class: str | None = None,
    failure_type: str | None = None,
    retry_class: str | None = None,
    retry_context: Mapping[str, Any] | None = None,
    pause_state_payload: Mapping[str, Any] | None = None,
    retry_after_seconds: int | None = None,
    whether_human_required: bool = False,
    next_action: str | None = None,
    reason: str | None = None,
    structured_result: Mapping[str, Any] | None = None,
    policy: Mapping[str, Any] | None = None,
    enforce_exhaustion_as_escalation: bool = True,
    now: Callable[[], datetime] = datetime.now,
) -> dict[str, Any]:
    retry_ctx = normalize_retry_context(retry_context)
    if is_pause_active(pause_state_payload) and not is_pause_resume_eligible(pause_state_payload, now=now):
        pause_payload = pause_state_payload if isinstance(pause_state_payload, Mapping) else {}
        return {
            "decision_kind": DECISION_PAUSE_AND_WAIT,
            "retry_class": None,
            "max_attempts": 0,
            "remaining_attempts": 0,
            "backoff_seconds": None,
            "pause_state": _normalize_text(pause_payload.get("pause_state"), default=PAUSE_STATE_OTHER),
            "pause_retry_after_seconds": _as_optional_int(pause_payload.get("retry_after_seconds")),
            "next_eligible_at": _normalize_text(pause_payload.get("next_eligible_at"), default="") or None,
            "whether_human_required": bool(pause_payload.get("whether_human_required", False)),
            "reason": "active pause state is not yet eligible for resume",
            "provider_class": normalize_provider_class(provider_name, provider_class),
            "operation_class": _normalize_text(operation_class, default="execution"),
            "failure_type": "paused_state_active",
            "matched_policy_id": None,
            "policy_found": False,
            "signal_source": "pause_state",
        }

    resolved_provider = normalize_provider_class(provider_name, provider_class)
    resolved_operation = _normalize_text(operation_class, default="execution")
    resolved_failure_type, signal_source = _resolve_failure_type(
        explicit_failure_type=failure_type,
        structured_result=structured_result,
        retry_after_seconds=retry_after_seconds,
        pause_state_payload=pause_state_payload,
        next_action=next_action,
        reason=reason,
    )

    if (
        isinstance(policy, Mapping)
        and isinstance(policy.get("entries"), list)
        and isinstance(policy.get("defaults"), Mapping)
    ):
        normalized_policy = dict(policy)
    elif isinstance(policy, Mapping):
        normalized_policy = normalize_retry_policy(policy)
    else:
        normalized_policy = load_retry_policy()
    matched = resolve_retry_policy_entry(
        normalized_policy,
        provider_class=resolved_provider,
        operation_class=resolved_operation,
        failure_type=resolved_failure_type,
        retry_class=retry_class,
    )
    policy_found = matched is not None
    selected = matched if matched is not None else _fallback_decision(
        failure_type=resolved_failure_type,
        next_action=next_action,
        retry_after_seconds=retry_after_seconds,
    )

    selected_retry_class = _resolve_retry_class(
        explicit_retry_class=retry_class,
        next_action=next_action,
        policy_retry_class=selected.get("retry_class") if isinstance(selected, Mapping) else None,
    )
    max_attempts = _as_non_negative_int(
        selected.get("max_attempts") if isinstance(selected, Mapping) else None,
        default=1,
    )
    backoff_schedule = selected.get("backoff_seconds") if isinstance(selected, Mapping) else (30,)
    if not isinstance(backoff_schedule, tuple):
        backoff_schedule = tuple(backoff_schedule) if isinstance(backoff_schedule, list) else (30,)
    backoff_schedule = tuple(_as_non_negative_int(value, default=0) for value in backoff_schedule) or (0,)

    decision_kind = _normalize_text(
        selected.get("decision_kind") if isinstance(selected, Mapping) else None,
        default=DECISION_ESCALATE_TO_HUMAN,
    )
    if decision_kind not in {
        DECISION_RETRY_NOW,
        DECISION_PAUSE_AND_WAIT,
        DECISION_TERMINAL_REFUSAL,
        DECISION_ESCALATE_TO_HUMAN,
    }:
        decision_kind = DECISION_ESCALATE_TO_HUMAN

    remaining_attempts = _compute_remaining_attempts(
        retry_context=retry_ctx,
        max_attempts=max_attempts,
        retry_class=selected_retry_class,
    )
    if enforce_exhaustion_as_escalation and decision_kind == DECISION_RETRY_NOW and remaining_attempts <= 0:
        decision_kind = DECISION_ESCALATE_TO_HUMAN

    selected_pause_state = _normalize_text(
        selected.get("pause_state") if isinstance(selected, Mapping) else None,
        default="",
    ) or None
    backoff_seconds = backoff_schedule[min(len(backoff_schedule) - 1, _as_non_negative_int(retry_ctx.get("prior_attempt_count"), default=0))]
    pause_retry_after = retry_after_seconds if retry_after_seconds is not None else backoff_seconds
    next_eligible_at = None
    if decision_kind == DECISION_PAUSE_AND_WAIT and pause_retry_after is not None:
        next_eligible_at = (now() + timedelta(seconds=max(0, pause_retry_after))).isoformat(timespec="seconds")

    human_required = bool(whether_human_required) or bool(selected.get("human_required", False))
    if decision_kind == DECISION_ESCALATE_TO_HUMAN:
        human_required = True

    if decision_kind == DECISION_TERMINAL_REFUSAL:
        reason_text = f"terminal refusal for failure_type={resolved_failure_type}"
    elif decision_kind == DECISION_PAUSE_AND_WAIT:
        reason_text = f"pause recommended for failure_type={resolved_failure_type}"
    elif decision_kind == DECISION_RETRY_NOW:
        reason_text = f"bounded retry allowed for failure_type={resolved_failure_type}"
    else:
        reason_text = f"human escalation required for failure_type={resolved_failure_type}"

    return {
        "decision_kind": decision_kind,
        "retry_class": selected_retry_class,
        "max_attempts": max_attempts,
        "remaining_attempts": remaining_attempts,
        "backoff_seconds": backoff_seconds if decision_kind == DECISION_RETRY_NOW else None,
        "pause_state": selected_pause_state if decision_kind == DECISION_PAUSE_AND_WAIT else None,
        "pause_retry_after_seconds": pause_retry_after if decision_kind == DECISION_PAUSE_AND_WAIT else None,
        "next_eligible_at": next_eligible_at,
        "whether_human_required": human_required,
        "reason": reason_text,
        "provider_class": resolved_provider,
        "operation_class": resolved_operation,
        "failure_type": resolved_failure_type,
        "matched_policy_id": _normalize_text(selected.get("id"), default="") or None,
        "policy_found": policy_found,
        "signal_source": signal_source,
        "evaluated_at": _iso_now(now),
    }

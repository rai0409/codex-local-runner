from __future__ import annotations

from typing import Any
from typing import Mapping

_ALLOWED_RETRY_CLASSES = {
    "same_prompt_retry",
    "repair_prompt_retry",
}
_DEFAULT_RETRY_BUDGET = 1


def _as_non_negative_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return max(0, value)
    if isinstance(value, str):
        text = value.strip()
        if text and text.isdigit():
            return int(text)
    return default


def _read_default_budget(policy_snapshot: Mapping[str, Any] | None) -> int:
    if not isinstance(policy_snapshot, Mapping):
        return _DEFAULT_RETRY_BUDGET

    for key in ("max_retry_budget", "retry_budget", "retry_budget_remaining"):
        value = policy_snapshot.get(key)
        if value is not None:
            return _as_non_negative_int(value, default=_DEFAULT_RETRY_BUDGET)

    retry_replan = policy_snapshot.get("retry_replan")
    if isinstance(retry_replan, Mapping):
        value = retry_replan.get("max_attempts")
        if value is not None:
            return _as_non_negative_int(value, default=_DEFAULT_RETRY_BUDGET)

    return _DEFAULT_RETRY_BUDGET


def normalize_retry_context(
    value: Mapping[str, Any] | None,
    *,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    default_budget = _read_default_budget(policy_snapshot)

    source = value if isinstance(value, Mapping) else {}
    prior_attempt_count = _as_non_negative_int(source.get("prior_attempt_count"), default=0)
    missing_signal_count = _as_non_negative_int(source.get("missing_signal_count"), default=0)
    retry_budget_remaining = _as_non_negative_int(
        source.get("retry_budget_remaining"),
        default=default_budget,
    )

    retry_class_raw = source.get("prior_retry_class")
    prior_retry_class = str(retry_class_raw).strip() if retry_class_raw is not None else ""
    if prior_retry_class not in _ALLOWED_RETRY_CLASSES:
        prior_retry_class = None

    return {
        "prior_attempt_count": prior_attempt_count,
        "prior_retry_class": prior_retry_class,
        "missing_signal_count": missing_signal_count,
        "retry_budget_remaining": retry_budget_remaining,
    }


def update_retry_context(
    *,
    current: Mapping[str, Any],
    next_action: str,
    observed_attempt_count: int,
) -> dict[str, Any]:
    prior_attempt_count = _as_non_negative_int(current.get("prior_attempt_count"), default=0)
    prior_retry_class = current.get("prior_retry_class")
    if not isinstance(prior_retry_class, str) or prior_retry_class not in _ALLOWED_RETRY_CLASSES:
        prior_retry_class = None
    missing_signal_count = _as_non_negative_int(current.get("missing_signal_count"), default=0)
    retry_budget_remaining = _as_non_negative_int(current.get("retry_budget_remaining"), default=0)

    observed = max(0, int(observed_attempt_count))
    prior_attempt_count = max(prior_attempt_count, observed)

    if next_action in _ALLOWED_RETRY_CLASSES:
        prior_retry_class = next_action
        prior_attempt_count += 1
        missing_signal_count = 0
        retry_budget_remaining = max(0, retry_budget_remaining - 1)
    elif next_action == "signal_recollect":
        missing_signal_count += 1
    else:
        missing_signal_count = 0

    return {
        "prior_attempt_count": prior_attempt_count,
        "prior_retry_class": prior_retry_class,
        "missing_signal_count": missing_signal_count,
        "retry_budget_remaining": retry_budget_remaining,
    }

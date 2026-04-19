from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_RETRY_POLICIES_PATH = "config/retry_policies.yaml"

DECISION_RETRY_NOW = "retry_now"
DECISION_PAUSE_AND_WAIT = "pause_and_wait"
DECISION_TERMINAL_REFUSAL = "terminal_refusal"
DECISION_ESCALATE_TO_HUMAN = "escalate_to_human"

DECISION_KINDS = {
    DECISION_RETRY_NOW,
    DECISION_PAUSE_AND_WAIT,
    DECISION_TERMINAL_REFUSAL,
    DECISION_ESCALATE_TO_HUMAN,
}

_DEFAULT_POLICY = {
    "schema_version": "v1",
    "defaults": {
        "decision_kind": DECISION_ESCALATE_TO_HUMAN,
        "max_attempts": 1,
        "backoff_seconds": (30,),
    },
    "entries": [],
}

_KNOWN_PAUSE_STATES = {
    "waiting_for_provider_capacity",
    "waiting_for_rate_limit_reset",
    "waiting_for_checks",
    "waiting_for_human",
    "paused_other_bounded",
}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip().lower()
    return text if text else default


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


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


def _normalize_backoff_seconds(value: Any, *, default: tuple[int, ...]) -> tuple[int, ...]:
    if value is None:
        return default
    if isinstance(value, (int, str)):
        parsed = _as_non_negative_int(value, default=-1)
        if parsed >= 0:
            return (parsed,)
        return default
    if not isinstance(value, list):
        return default
    normalized: list[int] = []
    for item in value:
        parsed = _as_non_negative_int(item, default=-1)
        if parsed >= 0:
            normalized.append(parsed)
    return tuple(normalized) if normalized else default


def _read_yaml(path: str) -> Mapping[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"retry policy: YAML parsing support is required to load '{path}', but 'yaml' is unavailable."
        ) from exc
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, Mapping):
        raise ValueError("retry policy YAML must contain a mapping root")
    return loaded


def _normalize_match_field(value: Any, *, default: str = "*") -> str:
    normalized = _normalize_text(value, default=default)
    return normalized or default


def _normalize_decision_kind(value: Any, *, default: str) -> str:
    normalized = _normalize_text(value, default=default)
    return normalized if normalized in DECISION_KINDS else default


def _normalize_entry(raw: Mapping[str, Any], *, index: int, defaults: Mapping[str, Any]) -> dict[str, Any] | None:
    match = _as_mapping(raw.get("match"))
    decision = _as_mapping(raw.get("decision"))

    provider_class = _normalize_match_field(
        (match or raw).get("provider_class"),
        default="*",
    )
    operation_class = _normalize_match_field(
        (match or raw).get("operation_class"),
        default="*",
    )
    failure_type = _normalize_match_field(
        (match or raw).get("failure_type"),
        default="*",
    )
    retry_class = _normalize_match_field(
        (match or raw).get("retry_class"),
        default="*",
    )

    decision_source = decision or raw
    default_kind = _normalize_decision_kind(
        defaults.get("decision_kind"),
        default=DECISION_ESCALATE_TO_HUMAN,
    )
    decision_kind = _normalize_decision_kind(
        decision_source.get("decision_kind"),
        default=default_kind,
    )
    max_attempts = _as_non_negative_int(
        decision_source.get("max_attempts"),
        default=_as_non_negative_int(defaults.get("max_attempts"), default=1),
    )
    backoff_seconds = _normalize_backoff_seconds(
        decision_source.get("backoff_seconds"),
        default=_normalize_backoff_seconds(defaults.get("backoff_seconds"), default=(30,)),
    )
    pause_state = _normalize_text(decision_source.get("pause_state"), default="") or None
    if pause_state is not None and pause_state not in _KNOWN_PAUSE_STATES:
        pause_state = None
    human_required = bool(decision_source.get("human_required", False))

    if provider_class == "*" and operation_class == "*" and failure_type == "*" and retry_class == "*":
        # Fully broad entries are allowed, but only if explicitly terminal/escalation-like.
        if decision_kind == DECISION_RETRY_NOW:
            return None

    policy_id = _normalize_text(raw.get("id"), default=f"policy_{index}")
    return {
        "id": policy_id,
        "index": index,
        "match": {
            "provider_class": provider_class,
            "operation_class": operation_class,
            "failure_type": failure_type,
            "retry_class": retry_class,
        },
        "decision_kind": decision_kind,
        "retry_class": _normalize_text(decision_source.get("retry_class"), default="") or None,
        "max_attempts": max_attempts,
        "backoff_seconds": backoff_seconds,
        "pause_state": pause_state,
        "human_required": human_required,
    }


def normalize_retry_policy(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return dict(_DEFAULT_POLICY)

    defaults_raw = _as_mapping(raw.get("defaults")) or {}
    defaults = {
        "decision_kind": _normalize_decision_kind(
            defaults_raw.get("decision_kind"),
            default=DECISION_ESCALATE_TO_HUMAN,
        ),
        "max_attempts": _as_non_negative_int(defaults_raw.get("max_attempts"), default=1),
        "backoff_seconds": _normalize_backoff_seconds(defaults_raw.get("backoff_seconds"), default=(30,)),
    }

    entries_raw = raw.get("policies")
    if not isinstance(entries_raw, list):
        entries_raw = []

    entries: list[dict[str, Any]] = []
    for idx, item in enumerate(entries_raw):
        if not isinstance(item, Mapping):
            continue
        normalized = _normalize_entry(item, index=idx, defaults=defaults)
        if normalized is None:
            continue
        entries.append(normalized)

    entries = sorted(entries, key=lambda item: (int(item["index"]), str(item["id"])))

    return {
        "schema_version": _normalize_text(raw.get("schema_version"), default="v1"),
        "defaults": defaults,
        "entries": entries,
    }


@lru_cache(maxsize=1)
def load_retry_policy(path: str = DEFAULT_RETRY_POLICIES_PATH) -> dict[str, Any]:
    loaded = _read_yaml(path)
    return normalize_retry_policy(loaded)


def _field_matches(policy_value: str, actual_value: str) -> bool:
    return policy_value == "*" or policy_value == actual_value


def _specificity(entry: Mapping[str, Any]) -> tuple[int, int, int, int, int]:
    match = _as_mapping(entry.get("match")) or {}
    return (
        1 if _normalize_text(match.get("provider_class"), default="*") != "*" else 0,
        1 if _normalize_text(match.get("operation_class"), default="*") != "*" else 0,
        1 if _normalize_text(match.get("failure_type"), default="*") != "*" else 0,
        1 if _normalize_text(match.get("retry_class"), default="*") != "*" else 0,
        -_as_non_negative_int(entry.get("index"), default=0),
    )


def resolve_retry_policy_entry(
    policy: Mapping[str, Any] | None,
    *,
    provider_class: str,
    operation_class: str,
    failure_type: str,
    retry_class: str | None = None,
) -> dict[str, Any] | None:
    if (
        isinstance(policy, Mapping)
        and isinstance(policy.get("entries"), list)
        and isinstance(policy.get("defaults"), Mapping)
    ):
        normalized_policy = dict(policy)
    else:
        normalized_policy = normalize_retry_policy(policy if isinstance(policy, Mapping) else None)
    entries = normalized_policy.get("entries")
    if not isinstance(entries, list):
        return None

    provider = _normalize_text(provider_class, default="generic")
    operation = _normalize_text(operation_class, default="generic")
    failure = _normalize_text(failure_type, default="unknown_failure")
    retry = _normalize_text(retry_class, default="*")

    matched: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        match = _as_mapping(entry.get("match")) or {}
        if not _field_matches(_normalize_text(match.get("provider_class"), default="*"), provider):
            continue
        if not _field_matches(_normalize_text(match.get("operation_class"), default="*"), operation):
            continue
        if not _field_matches(_normalize_text(match.get("failure_type"), default="*"), failure):
            continue
        if not _field_matches(_normalize_text(match.get("retry_class"), default="*"), retry):
            continue
        matched.append(dict(entry))

    if not matched:
        return None
    return sorted(matched, key=_specificity, reverse=True)[0]

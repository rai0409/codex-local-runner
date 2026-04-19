from __future__ import annotations

from datetime import datetime
from datetime import timedelta
import json
from pathlib import Path
import re
from typing import Any
from typing import Callable
from typing import Mapping

PAUSE_STATE_PROVIDER_CAPACITY = "waiting_for_provider_capacity"
PAUSE_STATE_RATE_LIMIT = "waiting_for_rate_limit_reset"
PAUSE_STATE_CHECKS = "waiting_for_checks"
PAUSE_STATE_HUMAN = "waiting_for_human"
PAUSE_STATE_OTHER = "paused_other_bounded"

PAUSE_STATES = {
    PAUSE_STATE_PROVIDER_CAPACITY,
    PAUSE_STATE_RATE_LIMIT,
    PAUSE_STATE_CHECKS,
    PAUSE_STATE_HUMAN,
    PAUSE_STATE_OTHER,
}

_PAUSE_FILENAME = "pause_state.json"
_PAUSE_SCHEMA_VERSION = "v1"

_RATE_LIMIT_PATTERNS = (
    "rate limit",
    "rate_limit",
    "retry-after",
    "retry after",
    "429",
    "too many requests",
)

_PROVIDER_CAPACITY_PATTERNS = (
    "provider capacity",
    "capacity unavailable",
    "capacity exhausted",
    "temporarily unavailable",
    "provider unavailable",
    "service unavailable",
    "overloaded",
)

_CHECK_WAIT_PATTERNS = (
    "wait for checks",
    "checks pending",
    "check pending",
    "checks not ready",
    "check status pending",
)

_RETRY_AFTER_PATTERN = re.compile(r"(?:retry[_ -]?after(?:[_ -]?seconds)?\s*[=:]?\s*)(\d+)", re.IGNORECASE)
_PROVIDER_PATTERN = re.compile(r"\b(codex|chatgpt|openai)\b", re.IGNORECASE)


def _iso_now(now: Callable[[], datetime]) -> str:
    return now().isoformat(timespec="seconds")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


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


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in patterns)


def _parse_iso_datetime(value: Any) -> datetime | None:
    text = _normalize_text(value, default="")
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _extract_provider_name(
    *,
    handoff_payload: Mapping[str, Any] | None,
    decision_payload: Mapping[str, Any] | None,
    reason_text: str,
) -> str | None:
    for payload in (handoff_payload, decision_payload):
        if not isinstance(payload, Mapping):
            continue
        provider_name = _normalize_text(payload.get("provider_name"), default="")
        if provider_name:
            return provider_name
        provider_name = _normalize_text(payload.get("provider"), default="")
        if provider_name:
            return provider_name
    match = _PROVIDER_PATTERN.search(reason_text)
    if match is None:
        return None
    return match.group(1).lower()


def _extract_retry_after_seconds(
    *,
    handoff_payload: Mapping[str, Any] | None,
    decision_payload: Mapping[str, Any] | None,
    reason_text: str,
) -> int | None:
    for payload in (handoff_payload, decision_payload):
        if not isinstance(payload, Mapping):
            continue
        retry_after = _as_optional_int(payload.get("retry_after_seconds"))
        if retry_after is not None and retry_after >= 0:
            return retry_after
        retry_after = _as_optional_int(payload.get("retry_after"))
        if retry_after is not None and retry_after >= 0:
            return retry_after
    match = _RETRY_AFTER_PATTERN.search(reason_text)
    if match is None:
        return None
    return int(match.group(1))


def _extract_next_eligible_at(
    *,
    handoff_payload: Mapping[str, Any] | None,
    decision_payload: Mapping[str, Any] | None,
) -> str | None:
    for payload in (handoff_payload, decision_payload):
        if not isinstance(payload, Mapping):
            continue
        direct = _parse_iso_datetime(payload.get("next_eligible_at"))
        if direct is not None:
            return direct.isoformat(timespec="seconds")
        retry_ctx = payload.get("updated_retry_context")
        if isinstance(retry_ctx, Mapping):
            nested = _parse_iso_datetime(retry_ctx.get("next_eligible_at"))
            if nested is not None:
                return nested.isoformat(timespec="seconds")
    return None


def _compute_next_eligible_at(
    *,
    retry_after_seconds: int | None,
    next_eligible_at: str | None,
    now: Callable[[], datetime],
) -> str | None:
    if next_eligible_at:
        parsed = _parse_iso_datetime(next_eligible_at)
        if parsed is not None:
            return parsed.isoformat(timespec="seconds")
    if retry_after_seconds is None:
        return None
    return (now() + timedelta(seconds=max(0, retry_after_seconds))).isoformat(timespec="seconds")


def classify_pause_condition(
    *,
    next_action: str,
    reason: str,
    whether_human_required: bool,
    handoff_payload: Mapping[str, Any] | None = None,
    decision_payload: Mapping[str, Any] | None = None,
    now: Callable[[], datetime] = datetime.now,
) -> dict[str, Any] | None:
    normalized_action = _normalize_text(next_action, default="")
    normalized_reason = _normalize_text(reason, default="")
    reason_text = normalized_reason.lower()

    explicit_state = _normalize_text(
        (handoff_payload or {}).get("pause_state") if isinstance(handoff_payload, Mapping) else "",
        default="",
    )
    if explicit_state and explicit_state not in PAUSE_STATES:
        explicit_state = PAUSE_STATE_OTHER

    retry_after_seconds = _extract_retry_after_seconds(
        handoff_payload=handoff_payload,
        decision_payload=decision_payload,
        reason_text=normalized_reason,
    )
    next_eligible_at = _compute_next_eligible_at(
        retry_after_seconds=retry_after_seconds,
        next_eligible_at=_extract_next_eligible_at(
            handoff_payload=handoff_payload,
            decision_payload=decision_payload,
        ),
        now=now,
    )
    provider_name = _extract_provider_name(
        handoff_payload=handoff_payload,
        decision_payload=decision_payload,
        reason_text=normalized_reason,
    )

    if _as_bool(whether_human_required):
        return {
            "pause_state": PAUSE_STATE_HUMAN,
            "pause_reason": normalized_reason or "human review required",
            "provider_name": provider_name,
            "retry_after_seconds": None,
            "next_eligible_at": None,
            "whether_human_required": True,
        }

    if normalized_action == "wait_for_checks" or _contains_any(reason_text, _CHECK_WAIT_PATTERNS):
        return {
            "pause_state": explicit_state or PAUSE_STATE_CHECKS,
            "pause_reason": normalized_reason or "waiting for checks",
            "provider_name": provider_name,
            "retry_after_seconds": retry_after_seconds,
            "next_eligible_at": next_eligible_at,
            "whether_human_required": False,
        }

    if _contains_any(reason_text, _RATE_LIMIT_PATTERNS):
        return {
            "pause_state": explicit_state or PAUSE_STATE_RATE_LIMIT,
            "pause_reason": normalized_reason or "provider rate limit encountered",
            "provider_name": provider_name,
            "retry_after_seconds": retry_after_seconds,
            "next_eligible_at": next_eligible_at,
            "whether_human_required": False,
        }

    if _contains_any(reason_text, _PROVIDER_CAPACITY_PATTERNS):
        return {
            "pause_state": explicit_state or PAUSE_STATE_PROVIDER_CAPACITY,
            "pause_reason": normalized_reason or "provider capacity temporarily unavailable",
            "provider_name": provider_name,
            "retry_after_seconds": retry_after_seconds,
            "next_eligible_at": next_eligible_at,
            "whether_human_required": False,
        }

    if explicit_state:
        return {
            "pause_state": explicit_state,
            "pause_reason": normalized_reason or "explicit bounded pause requested",
            "provider_name": provider_name,
            "retry_after_seconds": retry_after_seconds,
            "next_eligible_at": next_eligible_at,
            "whether_human_required": False,
        }

    return None


def pause_state_path(run_root: str | Path) -> Path:
    return Path(run_root) / _PAUSE_FILENAME


def build_pause_payload(
    *,
    job_id: str,
    pause_state: str,
    pause_reason: str,
    now: Callable[[], datetime] = datetime.now,
    run_id: str | None = None,
    provider_name: str | None = None,
    retry_after_seconds: int | None = None,
    next_eligible_at: str | None = None,
    resume_from_stage: str = "planned_execution_dispatch",
    whether_human_required: bool = False,
    preserved_inputs_summary: Mapping[str, Any] | None = None,
    previous_pause_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if pause_state not in PAUSE_STATES:
        pause_state = PAUSE_STATE_OTHER
    previous = previous_pause_payload if isinstance(previous_pause_payload, Mapping) else {}
    paused_at = _iso_now(now)
    resume_count = _as_optional_int(previous.get("resume_count")) or 0
    payload = {
        "pause_schema_version": _PAUSE_SCHEMA_VERSION,
        "job_id": _normalize_text(job_id, default=""),
        "run_id": _normalize_text(run_id, default="") or None,
        "lifecycle_state": "paused",
        "pause_state": pause_state,
        "pause_reason": _normalize_text(pause_reason, default=""),
        "provider_name": _normalize_text(provider_name, default="") or None,
        "retry_after_seconds": retry_after_seconds if retry_after_seconds is not None else None,
        "next_eligible_at": _normalize_text(next_eligible_at, default="") or None,
        "resume_from_stage": _normalize_text(resume_from_stage, default="planned_execution_dispatch"),
        "whether_human_required": _as_bool(whether_human_required),
        "preserved_inputs_summary": dict(preserved_inputs_summary or {}),
        "paused_at": _normalize_text(previous.get("paused_at"), default=paused_at),
        "updated_at": paused_at,
        "resume_count": max(0, resume_count),
        "last_resumed_at": _normalize_text(previous.get("last_resumed_at"), default="") or None,
    }
    return payload


def load_pause_payload(run_root: str | Path) -> dict[str, Any] | None:
    path = pause_state_path(run_root)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload


def persist_pause_payload(run_root: str | Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(run_root)
    root.mkdir(parents=True, exist_ok=True)
    normalized = dict(payload)
    pause_state = _normalize_text(normalized.get("pause_state"), default="")
    if pause_state not in PAUSE_STATES:
        normalized["pause_state"] = PAUSE_STATE_OTHER
    path = pause_state_path(root)
    path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return normalized


def is_pause_active(payload: Mapping[str, Any] | None) -> bool:
    if not isinstance(payload, Mapping):
        return False
    lifecycle_state = _normalize_text(payload.get("lifecycle_state"), default="paused")
    return lifecycle_state == "paused"


def is_pause_resume_eligible(
    payload: Mapping[str, Any] | None,
    *,
    now: Callable[[], datetime] = datetime.now,
) -> bool:
    if not is_pause_active(payload):
        return False
    pause_payload = payload if isinstance(payload, Mapping) else {}
    if _as_bool(pause_payload.get("manual_resume_requested")):
        return True

    pause_state = _normalize_text(pause_payload.get("pause_state"), default=PAUSE_STATE_OTHER)
    next_eligible_at = _parse_iso_datetime(pause_payload.get("next_eligible_at"))
    if next_eligible_at is not None:
        return now() >= next_eligible_at
    if pause_state == PAUSE_STATE_HUMAN:
        return False
    return False


def mark_pause_resumed(
    run_root: str | Path,
    *,
    now: Callable[[], datetime] = datetime.now,
    resume_reason: str = "pause_eligible_for_resume",
) -> dict[str, Any] | None:
    current = load_pause_payload(run_root)
    if not isinstance(current, Mapping):
        return None
    if not is_pause_active(current):
        return dict(current)

    resume_count = _as_optional_int(current.get("resume_count")) or 0
    resumed_at = _iso_now(now)
    updated = {
        **dict(current),
        "lifecycle_state": "resumed",
        "resume_count": max(0, resume_count) + 1,
        "last_resumed_at": resumed_at,
        "resume_reason": _normalize_text(resume_reason, default="pause_eligible_for_resume"),
        "updated_at": resumed_at,
    }
    return persist_pause_payload(run_root, updated)


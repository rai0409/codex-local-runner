from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from datetime import timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfoNotFoundError

OPERATOR_SCHEDULES_PATH = "config/operator_schedules.yaml"


def _as_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return value


def _as_string(value: Any, *, context: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{context} must be a non-empty string")
    return text


def _parse_daily_time(value: Any, *, context: str) -> tuple[str, int]:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{context} must be a non-empty string in HH:MM format")
    hour_text, sep, minute_text = text.partition(":")
    if sep != ":":
        raise ValueError(f"{context} must be in HH:MM format")
    if not hour_text.isdigit() or not minute_text.isdigit():
        raise ValueError(f"{context} must be in HH:MM format")
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"{context} must be in 24-hour HH:MM format")
    normalized = f"{hour:02d}:{minute:02d}"
    return normalized, (hour * 60) + minute


def _as_daily_times(value: Any, *, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    parsed: list[str] = []
    for index, item in enumerate(value):
        normalized, _ = _parse_daily_time(item, context=f"{context}[{index}]")
        parsed.append(normalized)
    if not parsed:
        raise ValueError(f"{context} must contain at least one time")
    return tuple(parsed)


def _load_yaml_file(path: str, *, context: str) -> Mapping[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"{context}: YAML parsing support is required to load '{path}', "
            "but 'yaml' is not available in the runtime environment."
        ) from exc

    loaded = yaml.safe_load(text)
    return _as_mapping(loaded, context=context)


@lru_cache(maxsize=1)
def load_operator_schedules(path: str = OPERATOR_SCHEDULES_PATH) -> dict[str, Any]:
    raw = _load_yaml_file(path, context="operator_schedules policy")
    schedules_raw = raw.get("schedules")
    if not isinstance(schedules_raw, list):
        raise ValueError("operator_schedules.schedules must be a list")

    schedules: list[dict[str, Any]] = []
    for index, entry in enumerate(schedules_raw):
        schedule = _as_mapping(entry, context=f"operator_schedules.schedules[{index}]")
        raw_schedule_id = schedule.get("schedule_id", schedule.get("name", f"schedule_{index}"))
        schedule_id = _as_string(raw_schedule_id, context=f"schedule[{index}].schedule_id")
        timezone_name = _as_string(schedule.get("timezone"), context=f"{schedule_id}.timezone")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"{schedule_id}.timezone is invalid: {timezone_name}") from exc

        trigger_raw = _as_mapping(schedule.get("trigger"), context=f"{schedule_id}.trigger")
        trigger_type = _as_string(trigger_raw.get("type"), context=f"{schedule_id}.trigger.type")
        trigger: dict[str, Any] = {"type": trigger_type}
        if trigger_type == "daily_times":
            times = _as_daily_times(
                trigger_raw.get("times"),
                context=f"{schedule_id}.trigger.times",
            )
            trigger["times"] = times
            trigger["daily_minutes"] = tuple(
                _parse_daily_time(time_value, context=f"{schedule_id}.trigger.times")[1]
                for time_value in times
            )
        else:
            # Keep unknown trigger fields for forward compatibility.
            for key, value in trigger_raw.items():
                if key != "type":
                    trigger[str(key)] = value

        target_raw: dict[str, Any]
        target_candidate = schedule.get("target")
        if target_candidate is None:
            # Backward-compatibility shim for older shape.
            target_raw = {"repo": schedule.get("target_repo")}
        else:
            target_raw = dict(_as_mapping(target_candidate, context=f"{schedule_id}.target"))
        target_repo = _as_string(target_raw.get("repo"), context=f"{schedule_id}.target.repo")

        delivery = _as_mapping(schedule.get("delivery"), context=f"{schedule_id}.delivery")
        decision = _as_mapping(schedule.get("decision"), context=f"{schedule_id}.decision")
        decision_mode = _as_string(
            decision.get("mode"),
            context=f"{schedule_id}.decision.mode",
        )
        if decision_mode == "advisory_only":
            # Backward-compatibility normalization.
            decision_mode = "human_review_required"

        schedules.append(
            {
                "schedule_id": schedule_id,
                # Keep compatibility with prior output consumers.
                "name": schedule_id,
                "enabled": bool(schedule.get("enabled", True)),
                "timezone": timezone_name,
                "target": {"repo": target_repo},
                # Keep compatibility with prior output consumers.
                "target_repo": target_repo,
                "job_selector": dict(
                    _as_mapping(schedule.get("job_selector"), context=f"{schedule_id}.job_selector")
                ),
                "delivery": {
                    "method": _as_string(
                        delivery.get("method"),
                        context=f"{schedule_id}.delivery.method",
                    )
                },
                "decision": {
                    "mode": decision_mode
                },
                "trigger": trigger,
            }
        )

    return {"schedules": tuple(schedules)}


def _is_trigger_due_now(trigger: Mapping[str, Any], *, local_now: datetime) -> bool:
    trigger_type = str(trigger.get("type", "")).strip()
    if trigger_type == "daily_times":
        daily_minutes = trigger.get("daily_minutes")
        if not isinstance(daily_minutes, tuple):
            return False
        now_minute = (local_now.hour * 60) + local_now.minute
        return now_minute in daily_minutes
    return False


def is_schedule_due_now(
    schedule: Mapping[str, Any],
    *,
    now_utc: datetime | None = None,
) -> bool:
    if not bool(schedule.get("enabled", False)):
        return False

    candidate_now = now_utc or datetime.now(timezone.utc)
    if candidate_now.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")

    schedule_timezone = _as_string(schedule.get("timezone"), context="schedule.timezone")
    local_now = candidate_now.astimezone(ZoneInfo(schedule_timezone))
    trigger = _as_mapping(schedule.get("trigger"), context="schedule.trigger")
    return _is_trigger_due_now(trigger, local_now=local_now)


def _normalize_schedule_for_runtime(
    schedule: Mapping[str, Any],
    *,
    index: int,
) -> dict[str, Any]:
    normalized = dict(schedule)

    raw_schedule_id = normalized.get("schedule_id", normalized.get("name", f"schedule_{index}"))
    normalized_schedule_id = _as_string(raw_schedule_id, context=f"schedule[{index}].schedule_id")
    normalized["schedule_id"] = normalized_schedule_id
    normalized.setdefault("name", normalized_schedule_id)

    if "target" not in normalized:
        target_repo = normalized.get("target_repo")
        if target_repo is not None:
            normalized["target"] = {"repo": str(target_repo).strip()}
    target = normalized.get("target")
    if isinstance(target, Mapping):
        repo_value = target.get("repo")
        if repo_value is not None:
            normalized["target_repo"] = str(repo_value).strip()

    decision = normalized.get("decision")
    if isinstance(decision, Mapping):
        mode = decision.get("mode")
        if str(mode).strip() == "advisory_only":
            normalized["decision"] = {"mode": "human_review_required"}

    trigger = normalized.get("trigger")
    if isinstance(trigger, Mapping):
        trigger_type = str(trigger.get("type", "")).strip()
        if trigger_type == "daily_times" and "daily_minutes" not in trigger:
            times = trigger.get("times")
            if isinstance(times, (list, tuple)):
                normalized_times = tuple(
                    _parse_daily_time(item, context=f"{normalized_schedule_id}.trigger.times")[0]
                    for item in times
                )
                daily_minutes = tuple(
                    _parse_daily_time(item, context=f"{normalized_schedule_id}.trigger.times")[1]
                    for item in normalized_times
                )
                normalized["trigger"] = {
                    "type": "daily_times",
                    "times": normalized_times,
                    "daily_minutes": daily_minutes,
                }

    return normalized


def get_due_operator_schedules(
    *,
    now_utc: datetime | None = None,
    schedule_policy: Mapping[str, Any] | None = None,
    path: str = OPERATOR_SCHEDULES_PATH,
) -> tuple[dict[str, Any], ...]:
    policy = schedule_policy if schedule_policy is not None else load_operator_schedules(path)
    schedules = policy.get("schedules")
    if not isinstance(schedules, (tuple, list)):
        raise ValueError("operator_schedules.schedules must be a list or tuple")

    due: list[dict[str, Any]] = []
    for index, schedule in enumerate(schedules):
        schedule_mapping = _as_mapping(schedule, context="operator_schedules.schedule")
        normalized_schedule = _normalize_schedule_for_runtime(schedule_mapping, index=index)
        if is_schedule_due_now(normalized_schedule, now_utc=now_utc):
            due.append(normalized_schedule)
    return tuple(due)

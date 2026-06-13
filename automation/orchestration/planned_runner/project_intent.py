"""Project Intent model (Prompt645).

A minimal, pure, offline, deterministic data model describing a project-level
development goal: what the project is, its success criteria, constraints, allowed
task kinds, bounded safety limits, and a human-approval / risk-boundary policy.

This is the first layer of the project-autonomy stack (Prompt641 architecture). It
performs NO execution: no Codex, no daemon queue, no network, no git, no enqueue.
Validation never raises on invalid input — it returns (normalized_model, errors) in
the same style as task_spec.validate_task_spec.

Safety limits are hard-bounded by the daemon caps so a project intent can never
request more than the bounded daemon candidate allows.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.planned_runner.task_spec import SUPPORTED_TASK_KINDS

PROJECT_INTENT_SCHEMA_VERSION = "v1"

# Mirrors scripts/run_task_queue_daemon.py caps (MAX_JOBS_CAP / MAX_CYCLES_CAP /
# MAX_SECONDS_TOTAL_CAP). Kept as local constants to avoid importing the script;
# they are the hard upper bounds for a project's safety_limits.
DAEMON_MAX_JOBS_CAP = 5
DAEMON_MAX_CYCLES_CAP = 2
DAEMON_MAX_SECONDS_TOTAL_CAP = 1800

# Risk categories a project may require human approval for. Open-ended but the known
# high-risk boundaries are documented here for callers.
KNOWN_RISK_CATEGORIES = ("push", "pr", "merge", "new_task_kind", "non_tmp_repo")

INTENT_SOURCES = ("manual", "generated")

_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")

_DEFAULT_SAFETY_LIMITS = {
    "max_tasks": DAEMON_MAX_JOBS_CAP,
    "max_cycles_per_task": 1,
    "max_total_seconds": DAEMON_MAX_SECONDS_TOTAL_CAP,
}


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_normalize_text(item) for item in value if _normalize_text(item)]


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    text = _normalize_text(value)
    if text.lstrip("-").isdigit():
        return int(text)
    return None


def _validate_safety_limits(raw: Any, errors: list[str]) -> dict[str, int]:
    limits = dict(_DEFAULT_SAFETY_LIMITS)
    if raw is None:
        return limits
    if not isinstance(raw, Mapping):
        errors.append("safety_limits must be an object")
        return limits
    bounds = {
        "max_tasks": DAEMON_MAX_JOBS_CAP,
        "max_cycles_per_task": DAEMON_MAX_CYCLES_CAP,
        "max_total_seconds": DAEMON_MAX_SECONDS_TOTAL_CAP,
    }
    for key, cap in bounds.items():
        if key not in raw:
            continue
        parsed = _as_int(raw.get(key))
        if parsed is None or parsed <= 0:
            errors.append(f"safety_limits.{key} must be a positive integer")
            continue
        if parsed > cap:
            errors.append(f"safety_limits.{key} must be <= daemon cap {cap}")
            continue
        limits[key] = parsed
    return limits


def _validate_approval_policy(raw: Any, errors: list[str]) -> dict[str, Any]:
    policy = {"require_human_approval": False, "approval_required_for": []}
    if raw is None:
        return policy
    if not isinstance(raw, Mapping):
        errors.append("human_approval_policy must be an object")
        return policy
    policy["require_human_approval"] = bool(raw.get("require_human_approval", False))
    policy["approval_required_for"] = _normalize_str_list(raw.get("approval_required_for"))
    return policy


def validate_project_intent(payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Validate a project intent object; returns (normalized intent, errors).

    Never raises on invalid input. Idempotent: validating a normalized intent
    returns an equal normalized intent with no new errors."""
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {}, ["project intent must be a JSON object"]

    project_id = _normalize_text(payload.get("project_id"))
    if not project_id or not _PROJECT_ID_PATTERN.match(project_id):
        errors.append("project_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")

    project_name = _normalize_text(payload.get("project_name"))
    if not project_name:
        errors.append("project_name is required")

    goal = _normalize_text(payload.get("goal"))
    if not goal:
        errors.append("goal is required")

    allowed_raw = payload.get("allowed_task_kinds")
    if allowed_raw is None:
        allowed_task_kinds = ["add_function"]
    else:
        allowed_task_kinds = _normalize_str_list(allowed_raw)
        if not allowed_task_kinds:
            errors.append("allowed_task_kinds must be a non-empty list when provided")
    unsupported = [k for k in allowed_task_kinds if k not in SUPPORTED_TASK_KINDS]
    if unsupported:
        errors.append(
            f"allowed_task_kinds contains unsupported kinds {unsupported}; "
            f"supported: {list(SUPPORTED_TASK_KINDS)}"
        )

    safety_limits = _validate_safety_limits(payload.get("safety_limits"), errors)
    approval_policy = _validate_approval_policy(payload.get("human_approval_policy"), errors)

    source = _normalize_text(payload.get("source"), default="manual")
    if source not in INTENT_SOURCES:
        errors.append(f"source must be one of {list(INTENT_SOURCES)}")

    intent = {
        "schema_version": _normalize_text(
            payload.get("schema_version"), default=PROJECT_INTENT_SCHEMA_VERSION
        ),
        "project_id": project_id,
        "project_name": project_name,
        "goal": goal,
        "success_criteria": _normalize_str_list(payload.get("success_criteria")),
        "constraints": _normalize_str_list(payload.get("constraints")),
        "allowed_task_kinds": allowed_task_kinds,
        "safety_limits": safety_limits,
        "human_approval_policy": approval_policy,
        "repo_target": _normalize_text(payload.get("repo_target")),
        "completion_criteria": _normalize_text(payload.get("completion_criteria")),
        "created_by": _normalize_text(payload.get("created_by")),
        "source": source,
        "notes": _normalize_text(payload.get("notes")),
    }
    return intent, errors


def project_intent_to_json(intent: Mapping[str, Any]) -> str:
    return json.dumps(dict(intent), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def project_intent_from_json(text: str) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}, ["project intent is not valid JSON"]
    return validate_project_intent(payload)


def load_project_intent(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}, [f"project intent unreadable: {path}"]
    return project_intent_from_json(text)


__all__ = [
    "PROJECT_INTENT_SCHEMA_VERSION",
    "DAEMON_MAX_JOBS_CAP",
    "DAEMON_MAX_CYCLES_CAP",
    "DAEMON_MAX_SECONDS_TOTAL_CAP",
    "KNOWN_RISK_CATEGORIES",
    "INTENT_SOURCES",
    "validate_project_intent",
    "project_intent_to_json",
    "project_intent_from_json",
    "load_project_intent",
]

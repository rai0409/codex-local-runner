"""Project prompt-batch model + validation (Prompt655).

A pure, offline, deterministic model for a *batch* of implementation prompts that an
operator / Claude Code / Codex will execute one at a time. This module ONLY models and
validates batches and manifests — it NEVER executes prompt text, runs tests, runs the
daemon/Codex, or mutates git. Validation is non-raising (returns errors lists).

Batch directory layout:
  prompts/project_batches/<batch_id>/
    manifest.json
    001_prompt_name.md
    002_prompt_name.md

Manifest schema (see validate_prompt_batch for rules).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

PROMPT_BATCH_SCHEMA_VERSION = "v1"
MAX_PROMPTS_CAP = 10

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _as_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return _normalize_text(value).lower() in {"1", "true", "yes", "y"}


def _is_safe_relpath(value: str) -> bool:
    """A repo-relative path with no absolute root, no '..', no leading slash."""
    text = _normalize_text(value)
    if not text:
        return False
    if text.startswith("/") or text.startswith("~"):
        return False
    if ".." in Path(text).parts:
        return False
    if "\x00" in text:
        return False
    return True


def _is_safe_tag(value: str) -> bool:
    return bool(_TAG_PATTERN.match(_normalize_text(value)))


def load_prompt_batch(batch_dir: str | Path) -> dict[str, Any]:
    """Read <batch_dir>/manifest.json. Returns {payload, errors}; never raises."""
    base = Path(batch_dir)
    manifest_path = base / "manifest.json"
    if not base.is_dir():
        return {"payload": {}, "errors": [f"batch dir not found: {base.as_posix()}"]}
    if not manifest_path.is_file():
        return {"payload": {}, "errors": [f"manifest.json not found in {base.as_posix()}"]}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"payload": {}, "errors": [f"manifest unreadable/invalid JSON: {exc}"]}
    if not isinstance(payload, Mapping):
        return {"payload": {}, "errors": ["manifest must be a JSON object"]}
    return {"payload": dict(payload), "errors": []}


def _validate_prompt_entry(
    raw: Any, index: int, batch_base: Path, seen_ids: set[str], errors: list[str]
) -> dict[str, Any]:
    loc = f"prompts[{index}]"
    if not isinstance(raw, Mapping):
        errors.append(f"{loc} must be an object")
        raw = {}
    prompt_id = _normalize_text(raw.get("prompt_id"))
    if not prompt_id or not _SLUG_PATTERN.match(prompt_id):
        errors.append(f"{loc}.prompt_id must match ^[a-z0-9][a-z0-9._-]{{0,63}}$")
    elif prompt_id in seen_ids:
        errors.append(f"{loc}.prompt_id duplicate: {prompt_id}")
    else:
        seen_ids.add(prompt_id)

    prompt_path = _normalize_text(raw.get("prompt_path"))
    prompt_exists = False
    if not _is_safe_relpath(prompt_path):
        errors.append(f"{loc}.prompt_path must be a batch-relative path (no absolute, no '..'): {prompt_path!r}")
    else:
        # Must resolve to a file strictly inside the batch dir.
        resolved = (batch_base / prompt_path).resolve()
        try:
            inside = resolved.is_relative_to(batch_base.resolve())
        except AttributeError:  # pragma: no cover - py<3.9 fallback
            inside = str(resolved).startswith(str(batch_base.resolve()))
        if not inside:
            errors.append(f"{loc}.prompt_path escapes the batch directory: {prompt_path!r}")
        elif not resolved.is_file():
            errors.append(f"{loc}.prompt_path file not found: {prompt_path!r}")
        else:
            prompt_exists = True

    expected_tag = _normalize_text(raw.get("expected_tag"))
    if expected_tag and not _is_safe_tag(expected_tag):
        errors.append(f"{loc}.expected_tag is not a safe tag name: {expected_tag!r}")

    expected_report = _normalize_text(raw.get("expected_report_path"))
    if expected_report and not _is_safe_relpath(expected_report):
        errors.append(f"{loc}.expected_report_path must be a repo-relative safe path: {expected_report!r}")
    expected_summary = _normalize_text(raw.get("expected_summary_path"))
    if expected_summary and not _is_safe_relpath(expected_summary):
        errors.append(f"{loc}.expected_summary_path must be a repo-relative safe path: {expected_summary!r}")

    required_tests = raw.get("required_tests", [])
    if required_tests and not (
        isinstance(required_tests, list) and all(isinstance(t, str) and t.strip() for t in required_tests)
    ):
        errors.append(f"{loc}.required_tests must be a list of non-empty strings")
        required_tests = []

    pass_conditions = raw.get("pass_conditions", {})
    status_field = ""
    status_value = ""
    if pass_conditions:
        if not isinstance(pass_conditions, Mapping):
            errors.append(f"{loc}.pass_conditions must be an object")
        else:
            status_field = _normalize_text(pass_conditions.get("status_field"))
            status_value = _normalize_text(pass_conditions.get("status_value"))

    return {
        "prompt_id": prompt_id,
        "prompt_path": prompt_path,
        "prompt_exists": prompt_exists,
        "expected_tag": expected_tag,
        "expected_report_path": expected_report,
        "expected_summary_path": expected_summary,
        "required_tests": [str(t) for t in (required_tests or [])],
        "pass_conditions": {"status_field": status_field, "status_value": status_value},
        "order": index,
    }


def validate_prompt_batch(
    batch_payload: Mapping[str, Any], batch_dir: str | Path
) -> tuple[dict[str, Any], list[str]]:
    """Validate a batch manifest payload. Returns (normalized_batch, errors). Never raises."""
    errors: list[str] = []
    if not isinstance(batch_payload, Mapping):
        return {}, ["batch manifest must be a JSON object"]
    batch_base = Path(batch_dir)

    batch_id = _normalize_text(batch_payload.get("batch_id"))
    if not batch_id or not _SLUG_PATTERN.match(batch_id):
        errors.append("batch_id must match ^[a-z0-9][a-z0-9._-]{0,63}$")

    goal = _normalize_text(batch_payload.get("goal"))
    if not goal:
        errors.append("goal is required")

    raw_max = batch_payload.get("max_prompts", MAX_PROMPTS_CAP)
    try:
        max_prompts = int(raw_max)
    except (TypeError, ValueError):
        max_prompts = 0
        errors.append("max_prompts must be an integer")
    if max_prompts < 1:
        errors.append("max_prompts must be >= 1")
    elif max_prompts > MAX_PROMPTS_CAP:
        errors.append(f"max_prompts must be <= cap {MAX_PROMPTS_CAP}")

    raw_prompts = batch_payload.get("prompts")
    prompts: list[dict[str, Any]] = []
    if not isinstance(raw_prompts, list) or not raw_prompts:
        errors.append("prompts must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, entry in enumerate(raw_prompts):
            prompts.append(_validate_prompt_entry(entry, index, batch_base, seen, errors))
        if max_prompts and len(prompts) > max_prompts:
            errors.append(f"prompts count {len(prompts)} exceeds max_prompts {max_prompts}")
        if len(prompts) > MAX_PROMPTS_CAP:
            errors.append(f"prompts count {len(prompts)} exceeds hard cap {MAX_PROMPTS_CAP}")

    batch = {
        "schema_version": _normalize_text(
            batch_payload.get("schema_version"), default=PROMPT_BATCH_SCHEMA_VERSION
        ),
        "batch_id": batch_id,
        "goal": goal,
        "max_prompts": max_prompts,
        "stop_on_failure": _as_bool(batch_payload.get("stop_on_failure"), default=True),
        "require_clean_source_before_each_prompt": _as_bool(
            batch_payload.get("require_clean_source_before_each_prompt"), default=True
        ),
        "require_commit_tag_per_prompt": _as_bool(
            batch_payload.get("require_commit_tag_per_prompt"), default=True
        ),
        "prompts": prompts,
    }
    return batch, errors


def load_and_validate(batch_dir: str | Path) -> tuple[dict[str, Any], list[str]]:
    loaded = load_prompt_batch(batch_dir)
    if loaded["errors"]:
        return {}, loaded["errors"]
    return validate_prompt_batch(loaded["payload"], batch_dir)


__all__ = [
    "PROMPT_BATCH_SCHEMA_VERSION",
    "MAX_PROMPTS_CAP",
    "load_prompt_batch",
    "validate_prompt_batch",
    "load_and_validate",
]

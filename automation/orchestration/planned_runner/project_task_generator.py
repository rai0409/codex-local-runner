"""Deterministic project task generator (Prompt646).

A pure, offline, NON-LLM generator that converts a validated ProjectIntent plus an
explicit list of structured task descriptors into a bounded ProjectTaskPlan that
passes the Prompt645 validators and stays backward compatible with the daemon
task-spec contract.

It performs NO execution: no Codex, no daemon queue, no enqueue, no network, no git.
Generation is fully deterministic (stable task ids / order / dependency wiring; no
Date.now()/random — any timestamp is an input). Free-text / LLM decomposition is out
of scope; the caller supplies structured descriptors.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from automation.orchestration.planned_runner.project_intent import (
    validate_project_intent,
)
from automation.orchestration.planned_runner.project_plan import (
    PROJECT_PLAN_SCHEMA_VERSION,
    validate_project_task_plan,
)

# Required task_spec payload fields per supported kind (mirrors task_spec.py).
_ADD_FUNCTION_REQUIRED = ("target_file", "function_name", "expression")
_SLUG_INVALID = re.compile(r"[^a-z0-9._-]+")
_TASK_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _slug(value: Any) -> str:
    text = _normalize_text(value).lower()
    if not text:
        return ""
    text = _SLUG_INVALID.sub("-", text).strip("-._")
    return text[:64]


def _result(status: str, errors: list[str], warnings: list[str], plan: dict[str, Any]) -> dict[str, Any]:
    return {"status": status, "errors": errors, "warnings": warnings, "plan": plan}


def generate_project_task_plan(
    intent: Mapping[str, Any],
    task_descriptors: Sequence[Mapping[str, Any]],
    *,
    generated_at: str = "",
) -> dict[str, Any]:
    """Generate a ProjectTaskPlan from a validated intent + structured descriptors.

    Returns {"status", "errors", "warnings", "plan"} and never raises. status is
    "success" only when the intent is valid, descriptors are within bounds, and the
    generated plan passes validate_project_task_plan with no errors."""
    errors: list[str] = []
    warnings: list[str] = []

    norm_intent, intent_errors = validate_project_intent(intent)
    if intent_errors:
        return _result("blocked", [f"intent.{e}" for e in intent_errors], warnings, {})

    allowed_kinds = list(norm_intent.get("allowed_task_kinds", []) or [])
    default_kind = allowed_kinds[0] if allowed_kinds else ""
    max_tasks = int(norm_intent.get("safety_limits", {}).get("max_tasks", 0) or 0)
    repo_target = norm_intent.get("repo_target", "")
    project_id = norm_intent.get("project_id", "")

    if not isinstance(task_descriptors, (list, tuple)):
        return _result("blocked", ["task_descriptors must be a list"], warnings, {})
    if len(task_descriptors) == 0:
        return _result("blocked", ["task_descriptors must be a non-empty list"], warnings, {})
    if max_tasks and len(task_descriptors) > max_tasks:
        return _result(
            "blocked",
            [f"task_descriptors count {len(task_descriptors)} exceeds safety_limits.max_tasks {max_tasks}"],
            warnings,
            {},
        )

    # Pass 1: deterministic task ids (descriptor-supplied id/name, else project-id+index).
    task_ids: list[str] = []
    for index, descriptor in enumerate(task_descriptors):
        explicit = ""
        if isinstance(descriptor, Mapping):
            explicit = _slug(descriptor.get("task_id") or descriptor.get("name"))
        tid = explicit or f"{project_id}-t{index:03d}"
        task_ids.append(tid)

    # Reference map for dependency resolution: by index (int or str) and by id/name.
    ref_map: dict[Any, str] = {}
    for index, (descriptor, tid) in enumerate(zip(task_descriptors, task_ids)):
        ref_map[index] = tid
        ref_map[str(index)] = tid
        ref_map[tid] = tid
        if isinstance(descriptor, Mapping):
            name = _slug(descriptor.get("name"))
            if name:
                ref_map[name] = tid

    # Pass 2: build tasks deterministically.
    tasks: list[dict[str, Any]] = []
    for index, (descriptor, tid) in enumerate(zip(task_descriptors, task_ids)):
        loc = tid or f"index {index}"
        if not isinstance(descriptor, Mapping):
            errors.append(f"descriptor[{index}] must be an object")
            continue
        if not _TASK_ID_PATTERN.match(tid):
            errors.append(f"descriptor[{index}] produced invalid task_id '{tid}'")

        kind = _normalize_text(descriptor.get("kind"), default=default_kind)

        payload: dict[str, Any] = {}
        if kind == "add_function":
            payload["repo_path"] = repo_target
            payload["target_file"] = _normalize_text(descriptor.get("target_file"))
            payload["function_name"] = _normalize_text(descriptor.get("function_name"))
            payload["expression"] = _normalize_text(descriptor.get("expression"))
            description = _normalize_text(descriptor.get("description"))
            if description:
                payload["description"] = description
            if descriptor.get("verify_commands") is not None:
                payload["verify_commands"] = descriptor.get("verify_commands")
            if descriptor.get("expected_unmodified_files") is not None:
                payload["expected_unmodified_files"] = descriptor.get("expected_unmodified_files")
            if descriptor.get("allow_extra_files") is not None:
                payload["allow_extra_files"] = bool(descriptor.get("allow_extra_files"))
            missing = [f for f in _ADD_FUNCTION_REQUIRED if not _normalize_text(payload.get(f))]
            if missing:
                errors.append(f"descriptor[{loc}] missing required add_function fields: {missing}")
        else:
            # Unsupported/not-allowed kind: still record the kind so the plan
            # validator flags it; provide a ref stub so the plan stays structurally valid.
            payload = {}

        # Dependency resolution (deterministic): refs may be index ints/strs or ids/names.
        deps: list[str] = []
        raw_deps = descriptor.get("depends_on")
        if isinstance(raw_deps, (list, tuple)):
            for ref in raw_deps:
                resolved = ref_map.get(ref)
                if resolved is None and isinstance(ref, str):
                    resolved = ref_map.get(_slug(ref))
                if resolved is None:
                    errors.append(f"descriptor[{loc}] has unresolved depends_on ref {ref!r}")
                elif resolved == tid:
                    errors.append(f"descriptor[{loc}] cannot depend on itself")
                elif resolved not in deps:
                    deps.append(resolved)

        task: dict[str, Any] = {
            "task_id": tid,
            "kind": kind,
            "task_spec_payload": payload,
            "depends_on": deps,
            "order": index,
            "status": "planned",
            "generated_task_spec_path": "",
        }
        if not payload:
            # No usable payload -> attach a stub ref so plan validation has a body to
            # check (the plan validator will still reject a not-allowed kind).
            task["generated_task_spec_ref"] = f"stub:{tid}"
        tasks.append(task)

    plan_payload = {
        "schema_version": PROJECT_PLAN_SCHEMA_VERSION,
        "intent": norm_intent,
        "tasks": tasks,
        "completion_criteria": _normalize_text(norm_intent.get("completion_criteria")),
        "generated_at": _normalize_text(generated_at),
        "source": "generated",
    }
    plan, plan_errors = validate_project_task_plan(plan_payload)
    errors.extend(plan_errors)

    status = "success" if not errors else "blocked"
    return _result(status, errors, warnings, plan)


__all__ = ["generate_project_task_plan"]

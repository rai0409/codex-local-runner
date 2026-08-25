"""Pure, deterministic replacement-task planning for verified terminal evidence."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from automation.orchestration.repository_multi_cycle_task_spec import (
    RepositoryMultiCycleTask,
    RepositoryMultiCycleTaskSpec,
    repository_multi_cycle_task_spec_to_mapping,
    serialize_repository_multi_cycle_task_spec,
    validate_repository_multi_cycle_task_spec,
)

ELIGIBLE_AUTO_REPLAN_REASON_CODES = frozenset({
    "single_task.task_completion.rework_exhausted",
    "single_task.task_scope.recovery_exhausted",
})
REPLAN_ENVELOPE_SCHEMA_VERSION = "1"
_ENVELOPE_FIELDS = frozenset({"schema_version", "decision", "prompt", "allowed_changed_paths", "commit_message"})


class RepositoryMultiCycleReplanError(ValueError):
    """Stable validation error for caller-verified replan input."""


@dataclass(frozen=True)
class ReplanFailureEvidence:
    predecessor_queue: RepositoryMultiCycleTaskSpec
    failed_task_index: int
    terminal_reason_code: str
    detail_reason_code: str | None = None
    completion_evidence: Mapping[str, Any] | None = None
    accepted_head_sha: str | None = None


@dataclass(frozen=True)
class ReplanEnvelope:
    decision: str
    prompt: str | None = None
    allowed_changed_paths: tuple[str, ...] = ()
    commit_message: str | None = None


@dataclass(frozen=True)
class ReplanPlan:
    status: str
    replacement_task: RepositoryMultiCycleTask | None
    successor_queue: RepositoryMultiCycleTaskSpec | None
    serialized_successor_queue: str | None
    successor_queue_sha256: str | None


def is_auto_replan_eligible(reason_code: str | None) -> bool:
    return reason_code in ELIGIBLE_AUTO_REPLAN_REASON_CODES


def validate_replan_envelope(value: Mapping[str, Any]) -> ReplanEnvelope:
    if not isinstance(value, Mapping):
        raise RepositoryMultiCycleReplanError("replan.envelope.invalid_type")
    unknown = set(value) - _ENVELOPE_FIELDS
    if unknown or value.get("schema_version") != REPLAN_ENVELOPE_SCHEMA_VERSION:
        raise RepositoryMultiCycleReplanError("replan.envelope.invalid_schema")
    decision = value.get("decision")
    if decision == "stop":
        if set(value) != {"schema_version", "decision"}:
            raise RepositoryMultiCycleReplanError("replan.envelope.stop_fields_invalid")
        return ReplanEnvelope("stop")
    if decision != "replace_failed_task":
        raise RepositoryMultiCycleReplanError("replan.envelope.decision_invalid")
    required = ("prompt", "allowed_changed_paths", "commit_message")
    if set(value) != {"schema_version", "decision", *required} or not isinstance(value["prompt"], str) or not value["prompt"].strip() or not isinstance(value["commit_message"], str) or not value["commit_message"].strip() or not isinstance(value["allowed_changed_paths"], list) or not value["allowed_changed_paths"]:
        raise RepositoryMultiCycleReplanError("replan.envelope.replacement_fields_invalid")
    return ReplanEnvelope("replace_failed_task", value["prompt"], tuple(value["allowed_changed_paths"]), value["commit_message"])


def replacement_task_id(failed_task_id: str, replan_attempt_number: int) -> str:
    if not isinstance(replan_attempt_number, int) or isinstance(replan_attempt_number, bool) or not 1 <= replan_attempt_number <= 99:
        raise RepositoryMultiCycleReplanError("replan.attempt.invalid")
    suffix = f"-replan-{replan_attempt_number}"
    if len(failed_task_id) + len(suffix) <= 64:
        return failed_task_id + suffix
    digest = hashlib.sha256(failed_task_id.encode("utf-8")).hexdigest()[:10]
    return failed_task_id[: 64 - len(suffix) - len(digest) - 1] + "-" + digest + suffix


def build_replacement_task(failed_task: RepositoryMultiCycleTask, envelope: ReplanEnvelope, replan_attempt_number: int) -> RepositoryMultiCycleTask:
    if envelope.decision != "replace_failed_task":
        raise RepositoryMultiCycleReplanError("replan.envelope.stop_has_no_task")
    raw: dict[str, Any] = {"schema_version":"1", "tasks":[{"task_id":replacement_task_id(failed_task.task_id, replan_attempt_number), "prompt":envelope.prompt, "allowed_changed_paths":list(envelope.allowed_changed_paths), "commit_message":envelope.commit_message}]}
    for name in ("execution_timeout_seconds", "validation_timeout_seconds", "completion_evaluator_timeout_seconds", "completion_rework_timeout_seconds"):
        value = getattr(failed_task, name)
        if value is not None:
            raw["tasks"][0][name] = value
    return validate_repository_multi_cycle_task_spec(raw).tasks[0]


def build_successor_queue(evidence: ReplanFailureEvidence, envelope: ReplanEnvelope, replan_attempt_number: int) -> ReplanPlan:
    if not is_auto_replan_eligible(evidence.terminal_reason_code):
        return ReplanPlan("noneligible", None, None, None, None)
    if not isinstance(evidence.failed_task_index, int) or not 0 <= evidence.failed_task_index < len(evidence.predecessor_queue.tasks):
        raise RepositoryMultiCycleReplanError("replan.failed_task_index.invalid")
    if envelope.decision == "stop":
        return ReplanPlan("stop", None, None, None, None)
    if evidence.terminal_reason_code == "single_task.task_scope.recovery_exhausted":
        recovery = dict(evidence.completion_evidence or {})
        effective = recovery.get("effective_allowed_changed_paths")
        trimmed = recovery.get("scope_trimmed_paths")
        if not (
            isinstance(effective, (list, tuple)) and isinstance(trimmed, (list, tuple))
            and all(isinstance(path, str) for path in (*effective, *trimmed))
        ):
            raise RepositoryMultiCycleReplanError("replan.scope_evidence.invalid")
        permitted = set(effective) | set(trimmed)
        selected = set(envelope.allowed_changed_paths)
        if not set(effective).issubset(selected) or not selected.issubset(permitted):
            raise RepositoryMultiCycleReplanError("replan.scope_paths.not_evidence_bounded")
    replacement = build_replacement_task(evidence.predecessor_queue.tasks[evidence.failed_task_index], envelope, replan_attempt_number)
    successor = validate_repository_multi_cycle_task_spec(RepositoryMultiCycleTaskSpec("1", (replacement, *evidence.predecessor_queue.tasks[evidence.failed_task_index + 1:])))
    serialized = serialize_repository_multi_cycle_task_spec(successor)
    return ReplanPlan("replace_failed_task", replacement, successor, serialized, hashlib.sha256(serialized.encode("utf-8")).hexdigest())


def build_replan_planner_prompt(evidence: ReplanFailureEvidence) -> str:
    safe = {key: value for key, value in dict(evidence.completion_evidence or {}).items() if key in {"status", "reason_code", "unsatisfied_criteria", "satisfied_criteria", "rework_attempted", "rework_validation_status", "rework_validation_reason", "declared_allowed_changed_paths", "effective_allowed_changed_paths", "original_unexpected_changed_files", "auto_expanded_paths", "scope_trimmed_paths", "scope_constrained_rework_attempted", "scope_constrained_rework_status", "post_trim_validation_status"}}
    scope_instruction = " For proven task-scope recovery exhaustion, preserve the objective and currently valid allowed paths; add only exact paths justified by verified recovery evidence, never directory/glob authority or unrelated files." if evidence.terminal_reason_code == "single_task.task_scope.recovery_exhausted" else ""
    return "PLANNING ONLY; do not implement or request Git operations. Return only JSON envelope schema_version=1 with decision replace_failed_task or stop. The model cannot set task_id, timeouts, queue metadata, or authority fields." + scope_instruction + " Verified evidence: " + json.dumps({"reason_code":evidence.terminal_reason_code,"detail_reason_code":evidence.detail_reason_code,"completion_evidence":safe}, ensure_ascii=True, sort_keys=True, separators=(",",":"))


__all__ = ["ELIGIBLE_AUTO_REPLAN_REASON_CODES", "ReplanEnvelope", "ReplanFailureEvidence", "ReplanPlan", "RepositoryMultiCycleReplanError", "build_replacement_task", "build_replan_planner_prompt", "build_successor_queue", "is_auto_replan_eligible", "replacement_task_id", "validate_replan_envelope"]

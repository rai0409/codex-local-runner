"""Fail-closed, read-only task-completion evaluation helpers.

This module deliberately separates material task completion from validation.
Its pure helpers neither invoke Git nor subprocesses; the one execution helper
uses the established Codex runner with prompt persistence disabled.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from run_codex import run_codex


TASK_COMPLETION_EVALUATION_BEGIN = "TASK_COMPLETION_EVALUATION_JSON_BEGIN"
TASK_COMPLETION_EVALUATION_END = "TASK_COMPLETION_EVALUATION_JSON_END"
MAX_EVALUATOR_OUTPUT_BYTES = 16_384
MAX_CRITERIA_ITEMS = 16
MAX_EVIDENCE_ITEMS = 16
MAX_ITEM_LENGTH = 500
MAX_REASON_CODE_LENGTH = 120
VALID_TASK_COMPLETION_STATUSES = frozenset({"completed", "needs_rework", "blocked"})


@dataclass(frozen=True)
class TaskCompletionEvaluation:
    status: str
    reason_code: str
    satisfied_criteria: tuple[str, ...]
    unsatisfied_criteria: tuple[str, ...]
    evidence_refs: tuple[str, ...]


def _blocked(reason_code: str) -> TaskCompletionEvaluation:
    return TaskCompletionEvaluation("blocked", reason_code, (), (), ())


def _bounded_strings(value: Any, *, maximum: int) -> tuple[str, ...] | None:
    if not isinstance(value, list) or len(value) > maximum:
        return None
    values: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or len(item) > MAX_ITEM_LENGTH:
            return None
        values.append(item.strip())
    return tuple(values)


def parse_task_completion_evaluation_output(output: Any) -> TaskCompletionEvaluation:
    """Parse exactly one bounded envelope, converting every fault to blocked."""
    if not isinstance(output, str) or len(output.encode("utf-8", errors="ignore")) > MAX_EVALUATOR_OUTPUT_BYTES:
        return _blocked("task_completion.output.unbounded")
    if output.count(TASK_COMPLETION_EVALUATION_BEGIN) != 1 or output.count(TASK_COMPLETION_EVALUATION_END) != 1:
        return _blocked("task_completion.envelope.invalid")
    begin = output.find(TASK_COMPLETION_EVALUATION_BEGIN) + len(TASK_COMPLETION_EVALUATION_BEGIN)
    end = output.find(TASK_COMPLETION_EVALUATION_END)
    if end < begin or output[:begin - len(TASK_COMPLETION_EVALUATION_BEGIN)].strip() or output[end + len(TASK_COMPLETION_EVALUATION_END):].strip():
        return _blocked("task_completion.envelope.invalid")
    try:
        value = json.loads(output[begin:end].strip())
    except (TypeError, ValueError):
        return _blocked("task_completion.json.invalid")
    if not isinstance(value, dict) or set(value) != {"status", "reason_code", "satisfied_criteria", "unsatisfied_criteria", "evidence_refs"}:
        return _blocked("task_completion.fields.invalid")
    status, reason_code = value.get("status"), value.get("reason_code")
    if status not in VALID_TASK_COMPLETION_STATUSES:
        return _blocked("task_completion.status.invalid")
    if not isinstance(reason_code, str) or not reason_code.strip() or len(reason_code) > MAX_REASON_CODE_LENGTH:
        return _blocked("task_completion.reason_code.invalid")
    satisfied = _bounded_strings(value.get("satisfied_criteria"), maximum=MAX_CRITERIA_ITEMS)
    unsatisfied = _bounded_strings(value.get("unsatisfied_criteria"), maximum=MAX_CRITERIA_ITEMS)
    evidence = _bounded_strings(value.get("evidence_refs"), maximum=MAX_EVIDENCE_ITEMS)
    if satisfied is None or unsatisfied is None or evidence is None:
        return _blocked("task_completion.lists.invalid")
    return TaskCompletionEvaluation(status, reason_code.strip(), satisfied, unsatisfied, evidence)


def task_completion_evaluation_to_mapping(value: TaskCompletionEvaluation) -> dict[str, Any]:
    return {key: item for key, item in asdict(value).items() if key in {"status", "reason_code", "satisfied_criteria", "unsatisfied_criteria", "evidence_refs"}}


def build_task_completion_evaluator_prompt(*, original_task: str, allowed_changed_paths: tuple[str, ...], changed_paths: tuple[str, ...], repository_state: Mapping[str, Any], diff_evidence: str, validation_evidence: Mapping[str, Any], artifact_evidence: Mapping[str, Any]) -> str:
    """Build the evaluator prompt from objective, bounded evidence only."""
    evidence = json.dumps({"allowed_changed_paths": list(allowed_changed_paths), "actual_changed_paths": list(changed_paths), "repository_state": dict(repository_state), "bounded_diff": diff_evidence, "safe_validation": dict(validation_evidence), "artifact_requirements": dict(artifact_evidence)}, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"""Mode: Scout\nYou are an independent task-completion evaluator. Inspect the current prepared worktree read-only. Do not edit files, run validation, weaken tests, or mutate Git.\n\nOriginal human-authored task:\n{original_task}\n\nObjective evidence (inspect it and the actual worktree; implementation stdout/stderr, implementation self-report, and review recommendations are forbidden evidence):\n{evidence}\n\nDecide whether the original task is materially satisfied. `completed` requires material satisfaction; `needs_rework` only identifies actionable deficiencies within allowed_changed_paths; `blocked` is required when safe completion cannot be established or would require forbidden/out-of-scope action. evidence_refs must be objective labels/paths/hashes, never raw prompt text.\n\nReturn exactly this envelope and nothing else:\n{TASK_COMPLETION_EVALUATION_BEGIN}\n{{\"status\":\"completed|needs_rework|blocked\",\"reason_code\":\"bounded.machine_code\",\"satisfied_criteria\":[\"non-empty bounded criterion\"],\"unsatisfied_criteria\":[],\"evidence_refs\":[\"objective evidence reference\"]}}\n{TASK_COMPLETION_EVALUATION_END}\n"""


def build_task_completion_rework_prompt(*, original_task: str, allowed_changed_paths: tuple[str, ...], evaluation: TaskCompletionEvaluation) -> str:
    return f"""Mode: Repair\nContinue in the CURRENT prepared worktree. Preserve valid existing changes and modify only these allowed paths: {json.dumps(list(allowed_changed_paths))}.\n\nOriginal task:\n{original_task}\n\nIndependent evaluator findings:\nreason_code: {evaluation.reason_code}\nunsatisfied_criteria: {json.dumps(list(evaluation.unsatisfied_criteria))}\nevidence_refs: {json.dumps(list(evaluation.evidence_refs))}\n\nFix only the actionable deficiencies above. Do not use implementation self-report as evidence. Do not weaken or modify tests/validation. Do not stage, commit, branch, reset, clean, stash, push, create a PR, merge, tag, release, or deploy.\n"""


def execute_task_completion_evaluator(*, worktree_path: str, run_root: str, prompt: str, runner: Callable[..., Mapping[str, Any]] = run_codex) -> TaskCompletionEvaluation:
    """Invoke the established Codex runner once, retaining no raw result here."""
    try:
        result = runner(task={"repo_path": worktree_path}, prompt=prompt, work_root=run_root, persist_prompt=False)
        if not isinstance(result, Mapping) or result.get("status") != "completed":
            return _blocked("task_completion.execution.failed")
        stdout_path = result.get("stdout_path")
        if not isinstance(stdout_path, str) or not stdout_path:
            return _blocked("task_completion.execution.output_missing")
        output_path = Path(stdout_path)
        if output_path.stat().st_size > MAX_EVALUATOR_OUTPUT_BYTES:
            return _blocked("task_completion.output.unbounded")
        output = output_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return _blocked("task_completion.execution.failed")
    return parse_task_completion_evaluation_output(output)


__all__ = [
    "MAX_EVALUATOR_OUTPUT_BYTES", "TASK_COMPLETION_EVALUATION_BEGIN", "TASK_COMPLETION_EVALUATION_END",
    "TaskCompletionEvaluation", "build_task_completion_evaluator_prompt", "build_task_completion_rework_prompt",
    "execute_task_completion_evaluator", "parse_task_completion_evaluation_output", "task_completion_evaluation_to_mapping",
]

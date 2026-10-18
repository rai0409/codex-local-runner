"""Pure deterministic helpers for bounded Safe Validation repair prompts."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import re
from typing import Any


MAX_VALIDATION_REPAIR_ATTEMPTS = 2
MAX_REPAIR_STREAM_CHARS = 4000
MAX_REPAIR_PROMPT_CHARS = 20000
_ACTIONABLE_STATUSES = frozenset(("failed", "timed_out", "spawn_failed"))
_TEST_IDENTIFIER = re.compile(r"(?m)^FAILED\s+([^\s]+)")


@dataclass(frozen=True)
class ValidationFailureClassification:
    """Bounded, machine-readable interpretation of Safe Validation evidence."""

    failure_class: str
    auto_repairable: bool
    retryable: bool
    failed_command_ids: tuple[str, ...]
    failed_test_identifiers: tuple[str, ...]
    scope_extension_required: bool
    evidence_refs: tuple[str, ...]


def validation_failure_classification_to_mapping(
    value: ValidationFailureClassification,
) -> dict[str, Any]:
    if not isinstance(value, ValidationFailureClassification):
        raise TypeError("value must be ValidationFailureClassification")
    result = asdict(value)
    for key in ("failed_command_ids", "failed_test_identifiers", "evidence_refs"):
        result[key] = list(result[key])
    return result


def _tail(value: str, limit: int = MAX_REPAIR_STREAM_CHARS) -> str:
    return value[-limit:]


def extract_actionable_failure(safe_validation: Mapping[str, Any] | Any) -> dict[str, Any] | None:
    """Return the first well-formed actionable command failure, in input order."""
    if not isinstance(safe_validation, Mapping):
        return None
    command_results = safe_validation.get("command_results")
    if not isinstance(command_results, Sequence) or isinstance(command_results, (str, bytes, bytearray)):
        return None
    for result in command_results:
        if not isinstance(result, Mapping) or result.get("status") not in _ACTIONABLE_STATUSES:
            continue
        command_id, kind = result.get("command_id"), result.get("kind")
        return_code, reason_code = result.get("return_code"), result.get("reason_code")
        stdout, stderr = result.get("stdout"), result.get("stderr")
        if (
            not isinstance(command_id, str) or not command_id
            or not isinstance(kind, str) or not kind
            or (return_code is not None and (isinstance(return_code, bool) or not isinstance(return_code, int)))
            or not isinstance(reason_code, str) or not reason_code
            or not isinstance(stdout, str) or not isinstance(stderr, str)
        ):
            return None
        return {
            "command_id": command_id,
            "kind": kind,
            "status": result["status"],
            "return_code": return_code,
            "reason_code": reason_code,
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
        }
    return None


def _failed_test_identifiers(command_results: Sequence[Any]) -> tuple[str, ...]:
    """Extract a small conventional pytest identifier set only when available."""
    values: list[str] = []
    for result in command_results:
        if not isinstance(result, Mapping):
            continue
        for stream in (result.get("stdout"), result.get("stderr")):
            if not isinstance(stream, str):
                continue
            for match in _TEST_IDENTIFIER.finditer(_tail(stream)):
                identifier = match.group(1)
                if len(identifier) <= 512 and identifier not in values:
                    values.append(identifier)
                    if len(values) == 20:
                        return tuple(values)
    return tuple(values)


def classify_validation_failure(
    safe_validation: Mapping[str, Any] | Any,
) -> ValidationFailureClassification:
    """Classify Safe Validation result metadata without public exception text.

    Command kind and argv are authoritative.  Output is consulted only for the
    optional, bounded pytest identifiers where the executor has no structured
    test-result field.
    """
    if not isinstance(safe_validation, Mapping):
        return ValidationFailureClassification("unknown", False, False, (), (), False, ())
    command_results = safe_validation.get("command_results")
    if not isinstance(command_results, Sequence) or isinstance(command_results, (str, bytes, bytearray)):
        return ValidationFailureClassification("unknown", False, False, (), (), False, ())
    failed = [
        result for result in command_results
        if isinstance(result, Mapping) and result.get("status") in _ACTIONABLE_STATUSES
    ]
    command_ids = tuple(
        result["command_id"] for result in failed
        if isinstance(result.get("command_id"), str) and result["command_id"]
    )
    if not failed or len(command_ids) != len(failed):
        return ValidationFailureClassification("unknown", False, False, command_ids, (), False, tuple(f"validation.command:{item}" for item in command_ids))
    first = failed[0]
    status = first.get("status")
    kind = first.get("kind")
    argv = first.get("argv")
    argv_text = " ".join(item for item in argv if isinstance(item, str)).casefold() if isinstance(argv, Sequence) and not isinstance(argv, (str, bytes, bytearray)) else ""
    kind_text = kind.casefold() if isinstance(kind, str) else ""
    evidence_refs = tuple(f"validation.command:{item}" for item in command_ids)
    if status == "timed_out":
        return ValidationFailureClassification("timeout", False, True, command_ids, (), False, evidence_refs)
    if status == "spawn_failed":
        return ValidationFailureClassification("infrastructure_failure", False, True, command_ids, (), False, evidence_refs)
    if "scope" in kind_text:
        return ValidationFailureClassification("scope_failure", False, False, command_ids, (), True, evidence_refs)
    if "compile" in kind_text or "py_compile" in argv_text:
        category = "compile_failure"
    elif "migration" in kind_text or "alembic" in argv_text or "migration" in argv_text:
        category = "migration_failure"
    elif "contract" in kind_text or "contract" in argv_text:
        category = "contract_failure"
    elif "import" in kind_text or re.search(r"\bimport\b", argv_text):
        category = "import_failure"
    elif kind_text in {"focused", "related_regression", "full"} or "pytest" in argv_text or "test" in kind_text:
        category = "test_failure"
    else:
        category = "unknown"
    repairable = category in {"test_failure", "compile_failure", "import_failure", "migration_failure", "contract_failure"}
    identifiers = _failed_test_identifiers(failed) if category == "test_failure" else ()
    return ValidationFailureClassification(category, repairable, False, command_ids, identifiers, False, evidence_refs)


def build_repair_prompt(
    original_prompt: str,
    repair_attempt_number: int,
    failure: Mapping[str, Any],
    allowed_changed_paths: Sequence[str] | None = None,
    *,
    classification: ValidationFailureClassification | None = None,
    current_changed_paths: Sequence[str] | None = None,
    remaining_repair_budget: int | None = None,
) -> str:
    """Build a bounded, deterministic repair instruction without executing anything."""
    if not isinstance(original_prompt, str):
        raise TypeError("original_prompt must be a string")
    if not isinstance(repair_attempt_number, int) or not 1 <= repair_attempt_number <= MAX_VALIDATION_REPAIR_ATTEMPTS:
        raise ValueError("repair_attempt_number is outside the supported bound")
    required = ("command_id", "kind", "status", "return_code", "reason_code", "stdout_tail", "stderr_tail")
    if not isinstance(failure, Mapping) or any(key not in failure for key in required):
        raise ValueError("failure must be an actionable failure context")
    if not all(isinstance(failure[key], str) for key in ("command_id", "kind", "status", "reason_code", "stdout_tail", "stderr_tail")):
        raise ValueError("failure context contains invalid text")
    if failure["return_code"] is not None and (isinstance(failure["return_code"], bool) or not isinstance(failure["return_code"], int)):
        raise ValueError("failure context contains invalid return_code")
    paths = tuple(allowed_changed_paths or ())
    if not all(isinstance(path, str) for path in paths):
        raise ValueError("allowed_changed_paths must contain strings")
    scope = "\n".join(f"- {path}" for path in paths) if paths else "No allowed_changed_paths were supplied."
    changed = tuple(current_changed_paths or ())
    if not all(isinstance(path, str) for path in changed):
        raise ValueError("current_changed_paths must contain strings")
    if remaining_repair_budget is not None and (isinstance(remaining_repair_budget, bool) or not isinstance(remaining_repair_budget, int) or remaining_repair_budget < 0):
        raise ValueError("remaining_repair_budget must be a nonnegative integer")
    classification_mapping = validation_failure_classification_to_mapping(classification) if classification is not None else {}
    classified = "\n".join(f"- {key}: {value}" for key, value in classification_mapping.items()) or "- unavailable"
    changed_scope = "\n".join(f"- {path}" for path in changed) or "- no changed paths recorded"
    safety = """Continue from the CURRENT prepared worktree and retain its existing diff; do not restart or reimplement the task. Repair only the demonstrated validation failure, preserve already-correct behavior, and remain inside effective_allowed_changed_paths. Do not edit the source repository directly. Do not redesign the task. Do not weaken validation merely to obtain a green result. Do not delete, skip, xfail, or broadly relax tests just to pass. Do not modify Repository Profile validation commands to bypass failure. Do not stage files; do not commit; do not switch, create, or delete branches; do not reset; do not revert unrelated valid changes; do not clean; do not stash; do not push; do not create a PR; do not merge; do not tag; do not release; do not deploy."""
    prefix = f"""Autonomous validation repair attempt {repair_attempt_number} of {MAX_VALIDATION_REPAIR_ATTEMPTS}.

Original task objective:
"""
    details = f"""

Effective allowed changed paths (modify only these):
{scope}

Current changed paths:
{changed_scope}

Failure classification:
{classified}

Remaining repair budget after this attempt: {remaining_repair_budget if remaining_repair_budget is not None else "unknown"}

Safe Validation failure:
- command_id: {failure["command_id"]}
- kind: {failure["kind"]}
- status: {failure["status"]}
- return_code: {failure["return_code"]}
- reason_code: {failure["reason_code"]}

{safety}

Bounded stdout tail:
"""
    suffix = "\n\nBounded stderr tail:\n"
    # Keep safety and objective before output. Output is reduced first.
    fixed_length = len(prefix) + len(details) + len(suffix)
    available = max(0, MAX_REPAIR_PROMPT_CHARS - fixed_length)
    objective = original_prompt[:available]
    available -= len(objective)
    stdout_tail = failure["stdout_tail"][-min(len(failure["stdout_tail"]), available):]
    available -= len(stdout_tail)
    stderr_tail = failure["stderr_tail"][-min(len(failure["stderr_tail"]), available):]
    return (prefix + objective + details + stdout_tail + suffix + stderr_tail)[:MAX_REPAIR_PROMPT_CHARS]


__all__ = [
    "MAX_REPAIR_PROMPT_CHARS", "MAX_REPAIR_STREAM_CHARS", "MAX_VALIDATION_REPAIR_ATTEMPTS",
    "ValidationFailureClassification", "build_repair_prompt", "classify_validation_failure",
    "extract_actionable_failure", "validation_failure_classification_to_mapping",
]

"""Pure deterministic helpers for bounded Safe Validation repair prompts."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


MAX_VALIDATION_REPAIR_ATTEMPTS = 2
MAX_REPAIR_STREAM_CHARS = 4000
MAX_REPAIR_PROMPT_CHARS = 20000
_ACTIONABLE_STATUSES = frozenset(("failed", "timed_out", "spawn_failed"))


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


def build_repair_prompt(
    original_prompt: str,
    repair_attempt_number: int,
    failure: Mapping[str, Any],
    allowed_changed_paths: Sequence[str] | None = None,
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
    safety = """Continue from the CURRENT prepared worktree. Inspect and preserve valid existing task changes. Fix the root cause represented by the validation failure and remain within the original task objective. Do not weaken validation merely to obtain a green result. Do not delete, skip, xfail, or broadly relax tests just to pass. Do not modify Repository Profile validation commands to bypass failure. Do not stage files; do not commit; do not switch, create, or delete branches; do not reset; do not restore unrelated changes; do not clean; do not stash; do not push; do not create a PR; do not merge; do not tag; do not release; do not deploy."""
    prefix = f"""Autonomous validation repair attempt {repair_attempt_number} of {MAX_VALIDATION_REPAIR_ATTEMPTS}.

Original task objective:
"""
    details = f"""

Allowed changed paths (modify only these when supplied):
{scope}

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
    "build_repair_prompt", "extract_actionable_failure",
]

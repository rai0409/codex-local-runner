"""Strict effect-verification success gate (Prompt638B).

Single source of truth for the question: "did effect verification strictly
pass?". Shared by the autonomous cycle classifier, the autonomous live loop
(final status), and the daemon queue runner (commit/tag + queue routing).

Closes the Prompt638A safety bug
(effect_failed_not_gated_before_success_commit_tag) where a failed effect
verification with a zero Codex returncode was promoted to final success and a
sandbox commit/tag.

Policy:
- Any explicit hard-failure status ("failed"/"blocked"/...) blocks success,
  unconditionally — even when effect verification was not nominally expected.
- When effect verification was expected, EVERY per-cycle status must be exactly
  "passed". An empty list, "not_run", "", or null all block success.
- When effect verification was not expected and no hard failure is present, the
  gate passes so legacy no-effect-spec flows stay green.
"""
from __future__ import annotations

from typing import Any, Iterable

REQUIRED_EFFECT_STATUS = "passed"

# Statuses that are an explicit, unconditional failure signal: these block
# success regardless of whether effect verification was nominally "expected".
HARD_FAILURE_EFFECT_STATUSES = frozenset(
    {"failed", "failure", "blocked", "timeout", "execution_error", "error", "missing"}
)


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_effect_statuses(statuses: Iterable[Any] | None) -> list[str]:
    return [_normalize(status) for status in (statuses or [])]


def evaluate_strict_effect_gate(
    statuses: Iterable[Any] | None,
    *,
    effect_expected: bool = True,
) -> dict[str, Any]:
    """Return a strict gate verdict for the given per-cycle effect statuses.

    The returned dict always contains:
    - passed: bool — True only if effect verification strictly succeeded.
    - reason: str — "none" when passed, otherwise a short failure reason.
    - statuses: list[str] — normalized (lowercased/stripped) input statuses.
    - non_passed_statuses: list[str] — normalized statuses that are not "passed".
    """
    normalized = normalize_effect_statuses(statuses)
    hard_failures = [s for s in normalized if s in HARD_FAILURE_EFFECT_STATUSES]
    non_passed = [s for s in normalized if s != REQUIRED_EFFECT_STATUS]

    if hard_failures:
        return {
            "passed": False,
            "reason": "effect_verification_failed",
            "statuses": normalized,
            "non_passed_statuses": non_passed,
        }
    if effect_expected:
        if not normalized:
            return {
                "passed": False,
                "reason": "effect_verification_missing",
                "statuses": normalized,
                "non_passed_statuses": non_passed,
            }
        if non_passed:
            return {
                "passed": False,
                "reason": "effect_verification_not_passed",
                "statuses": normalized,
                "non_passed_statuses": non_passed,
            }
    return {
        "passed": True,
        "reason": "none",
        "statuses": normalized,
        "non_passed_statuses": [],
    }


def strict_effect_success(
    statuses: Iterable[Any] | None,
    *,
    effect_expected: bool = True,
) -> bool:
    """Convenience boolean wrapper around :func:`evaluate_strict_effect_gate`."""
    return bool(
        evaluate_strict_effect_gate(statuses, effect_expected=effect_expected)["passed"]
    )


__all__ = [
    "REQUIRED_EFFECT_STATUS",
    "HARD_FAILURE_EFFECT_STATUSES",
    "normalize_effect_statuses",
    "evaluate_strict_effect_gate",
    "strict_effect_success",
]

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from orchestrator.schemas import MergeGateResult
from orchestrator.schemas import RubricEvaluationResult


def _policy_bool(policy: Mapping[str, Any], key: str, default: bool) -> bool:
    return bool(policy.get(key, default))


def _policy_categories(policy: Mapping[str, Any]) -> tuple[str, ...]:
    value = policy.get("auto_merge_categories", ())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def apply_merge_gate(
    *,
    rubric: RubricEvaluationResult,
    policy: Mapping[str, Any],
) -> MergeGateResult:
    fail_reasons: list[str] = []

    if _policy_bool(policy, "require_rubric_all_pass", True) and not rubric.merge_eligible:
        if rubric.fail_reasons:
            fail_reasons.extend(rubric.fail_reasons)
        else:
            fail_reasons.append("rubric_not_all_pass")

    if _policy_bool(policy, "require_ci_green", True) and not rubric.ci_required_checks_green:
        fail_reasons.append("required_ci_checks_not_green")

    if _policy_bool(policy, "require_declared_equals_observed_category", True):
        if rubric.declared_category != rubric.observed_category:
            fail_reasons.append("declared_category_does_not_match_observed_category")

    if _policy_bool(policy, "require_no_forbidden_paths_touched", True):
        if not rubric.forbidden_files_untouched:
            fail_reasons.append("observed_category_forbidden_paths_touched")

    if _policy_bool(policy, "require_diff_size_within_limit", True):
        if not rubric.diff_size_within_limit:
            fail_reasons.append("diff_size_limit_exceeded")

    auto_merge_categories = _policy_categories(policy)
    auto_merge_allowed = rubric.observed_category in auto_merge_categories
    if not auto_merge_allowed:
        fail_reasons.append("category_not_auto_merge_allowed")

    deduped: list[str] = []
    for reason in fail_reasons:
        if reason not in deduped:
            deduped.append(reason)

    passed = len(deduped) == 0 and auto_merge_allowed
    return MergeGateResult(
        passed=passed,
        fail_reasons=tuple(deduped),
        auto_merge_allowed=auto_merge_allowed,
    )

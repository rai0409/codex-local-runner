from __future__ import annotations

from fnmatch import fnmatch
from collections.abc import Mapping, Sequence
from typing import Any

from orchestrator.policy_loader import load_merge_gate_policy
from orchestrator.schemas import MergeGateResult
from orchestrator.schemas import RubricEvaluationResult


def _policy_bool(policy: Mapping[str, Any], key: str, default: bool) -> bool:
    return bool(policy.get(key, default))


def _policy_categories(policy: Mapping[str, Any]) -> tuple[str, ...]:
    value = policy.get("auto_merge_categories", ())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _policy_auto_progression(policy: Mapping[str, Any]) -> dict[str, Any]:
    raw = policy.get("auto_progression", {})
    if not isinstance(raw, Mapping):
        return {
            "policy_eligible_categories": (),
            "auto_pr_candidate_categories": (),
            "max_changed_files": 0,
            "max_total_diff_lines": 0,
            "generated_path_patterns": (),
            "binary_file_extensions": (),
        }

    def _tuple(key: str) -> tuple[str, ...]:
        value = raw.get(key, ())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()

    def _non_negative_int(key: str) -> int:
        value = raw.get(key, 0)
        if isinstance(value, bool):
            return 0
        if isinstance(value, int):
            return max(value, 0)
        if isinstance(value, str):
            text = value.strip()
            if text and text.isdigit():
                return int(text)
        return 0

    return {
        "policy_eligible_categories": _tuple("policy_eligible_categories"),
        "auto_pr_candidate_categories": _tuple("auto_pr_candidate_categories"),
        "max_changed_files": _non_negative_int("max_changed_files"),
        "max_total_diff_lines": _non_negative_int("max_total_diff_lines"),
        "generated_path_patterns": _tuple("generated_path_patterns"),
        "binary_file_extensions": tuple(ext.lower() for ext in _tuple("binary_file_extensions")),
    }


def _normalize_paths(changed_files: Sequence[str] | None) -> tuple[str, ...]:
    if not changed_files:
        return ()
    normalized: list[str] = []
    for raw in changed_files:
        path = str(raw).strip().replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        if path:
            normalized.append(path)
    return tuple(sorted(set(normalized)))


def _is_generated_path(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def _is_binary_path(path: str, binary_extensions: tuple[str, ...]) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(ext) for ext in binary_extensions)


def _derive_progression_policy(
    *,
    rubric: RubricEvaluationResult,
    changed_files: tuple[str, ...],
    additions: int,
    deletions: int,
    policy: Mapping[str, Any],
) -> tuple[str, bool, bool, tuple[str, ...]]:
    reasons: list[str] = []
    auto_progression = _policy_auto_progression(policy)
    policy_categories = set(auto_progression["policy_eligible_categories"])
    auto_pr_categories = set(auto_progression["auto_pr_candidate_categories"])
    auto_pr_categories = auto_pr_categories.intersection(policy_categories)

    observed_category = str(rubric.observed_category).strip()
    declared_category = str(rubric.declared_category).strip()
    total_diff_lines = int(additions) + int(deletions)

    if declared_category != observed_category:
        reasons.append("declared_category_does_not_match_observed_category")
    if observed_category not in policy_categories:
        reasons.append("category_not_policy_eligible")

    if not rubric.forbidden_files_untouched:
        reasons.append("observed_category_forbidden_paths_touched")
    if not rubric.diff_size_within_limit:
        reasons.append("diff_size_limit_exceeded")
    if not rubric.required_tests_declared:
        reasons.append("required_tests_not_declared")
    if not rubric.required_tests_executed:
        reasons.append("required_tests_not_executed")
    if not rubric.required_tests_passed:
        reasons.append("required_tests_not_passed")
    if not rubric.ci_required_checks_green:
        reasons.append("required_ci_checks_not_green")

    if not changed_files:
        reasons.append("changed_files_missing")
    max_changed_files = int(auto_progression["max_changed_files"])
    if max_changed_files > 0 and len(changed_files) > max_changed_files:
        reasons.append("changed_files_count_exceeded")

    max_total_diff_lines = int(auto_progression["max_total_diff_lines"])
    if max_total_diff_lines > 0 and total_diff_lines > max_total_diff_lines:
        reasons.append("total_diff_lines_exceeded")

    generated_patterns = tuple(auto_progression["generated_path_patterns"])
    if generated_patterns and any(_is_generated_path(path, generated_patterns) for path in changed_files):
        reasons.append("generated_path_touched")

    binary_extensions = tuple(auto_progression["binary_file_extensions"])
    if binary_extensions and any(_is_binary_path(path, binary_extensions) for path in changed_files):
        reasons.append("binary_file_touched")

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)

    if deduped:
        return "manual_only", False, False, tuple(deduped)

    policy_eligible = True
    auto_pr_candidate = observed_category in auto_pr_categories
    progression_state = "auto_pr_candidate" if auto_pr_candidate else "policy_eligible"
    return progression_state, policy_eligible, auto_pr_candidate, ()


def apply_merge_gate(
    *,
    rubric: RubricEvaluationResult,
    policy: Mapping[str, Any] | None = None,
    changed_files: Sequence[str] | None = None,
    additions: int = 0,
    deletions: int = 0,
) -> MergeGateResult:
    effective_policy = policy if policy is not None else load_merge_gate_policy()
    fail_reasons: list[str] = []

    if _policy_bool(effective_policy, "require_rubric_all_pass", True) and not rubric.merge_eligible:
        if rubric.fail_reasons:
            fail_reasons.extend(rubric.fail_reasons)
        else:
            fail_reasons.append("rubric_not_all_pass")

    if _policy_bool(effective_policy, "require_ci_green", True) and not rubric.ci_required_checks_green:
        fail_reasons.append("required_ci_checks_not_green")

    if _policy_bool(effective_policy, "require_declared_equals_observed_category", True):
        if rubric.declared_category != rubric.observed_category:
            fail_reasons.append("declared_category_does_not_match_observed_category")

    if _policy_bool(effective_policy, "require_no_forbidden_paths_touched", True):
        if not rubric.forbidden_files_untouched:
            fail_reasons.append("observed_category_forbidden_paths_touched")

    if _policy_bool(effective_policy, "require_diff_size_within_limit", True):
        if not rubric.diff_size_within_limit:
            fail_reasons.append("diff_size_limit_exceeded")

    auto_merge_categories = _policy_categories(effective_policy)
    auto_merge_allowed = rubric.observed_category in auto_merge_categories
    if not auto_merge_allowed:
        fail_reasons.append("category_not_auto_merge_allowed")

    deduped: list[str] = []
    for reason in fail_reasons:
        if reason not in deduped:
            deduped.append(reason)

    passed = len(deduped) == 0 and auto_merge_allowed
    normalized_changed_files = _normalize_paths(changed_files)
    progression_state, policy_eligible, auto_pr_candidate, progression_fail_reasons = (
        _derive_progression_policy(
            rubric=rubric,
            changed_files=normalized_changed_files,
            additions=additions,
            deletions=deletions,
            policy=effective_policy,
        )
    )
    return MergeGateResult(
        passed=passed,
        fail_reasons=tuple(deduped),
        auto_merge_allowed=auto_merge_allowed,
        progression_state=progression_state,
        policy_eligible=policy_eligible,
        auto_pr_candidate=auto_pr_candidate,
        progression_fail_reasons=progression_fail_reasons,
    )

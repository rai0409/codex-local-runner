from __future__ import annotations

from collections.abc import Mapping
from fnmatch import fnmatch
from typing import Iterable

from orchestrator.policy_loader import get_change_category_policy
from orchestrator.schemas import RubricEvaluationResult

_RUNTIME_SENSITIVE_EXACT = {"run_codex.py", "app.py"}
_RUNTIME_SENSITIVE_PREFIXES = ("adapters/", "verify/", "workspace/")
_CONTRACT_SHAPE_PATHS = {"adapters/codex_cli.py", "docs/reviewer_handoff.md"}


def _normalize_paths(changed_files: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in changed_files:
        path = str(raw).strip().replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        if path:
            normalized.append(path)
    return tuple(sorted(set(normalized)))


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) for pattern in patterns)


def _is_runtime_sensitive(path: str) -> bool:
    if path in _RUNTIME_SENSITIVE_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _RUNTIME_SENSITIVE_PREFIXES)


def evaluate_rubric(
    *,
    declared_category: str,
    observed_category: str,
    changed_files: Iterable[str],
    additions: int,
    deletions: int,
    required_tests_declared: bool,
    required_tests_executed: bool,
    required_tests_passed: bool,
    ci_green: bool,
    rollback_metadata_recorded: bool,
    diff_line_limit: int = 400,
    change_categories_policy: Mapping[str, object] | None = None,
) -> RubricEvaluationResult:
    paths = _normalize_paths(changed_files)
    rules = get_change_category_policy(
        observed_category,
        change_categories_policy=change_categories_policy,
    )

    if rules is None:
        allowed_files_only = False
        forbidden_files_untouched = False
    else:
        allowed_patterns = tuple(str(item) for item in rules.get("allowed_paths", ()))
        forbidden_patterns = tuple(str(item) for item in rules.get("forbidden_paths", ()))
        allowed_files_only = all(_matches_any(path, allowed_patterns) for path in paths)
        forbidden_files_untouched = not any(
            _matches_any(path, forbidden_patterns) for path in paths
        )

    diff_size_within_limit = (int(additions) + int(deletions)) <= int(diff_line_limit)
    declared_equals_observed = str(declared_category).strip() == str(observed_category).strip()

    runtime_semantics_changed = any(_is_runtime_sensitive(path) for path in paths)
    contract_shape_changed = any(path in _CONTRACT_SHAPE_PATHS for path in paths)
    reviewer_fields_changed = any(path in _CONTRACT_SHAPE_PATHS for path in paths)

    fail_reasons: list[str] = []
    if not declared_equals_observed:
        fail_reasons.append("declared_category_does_not_match_observed_category")
    if not allowed_files_only:
        fail_reasons.append("observed_category_allowed_paths_violated")
    if not forbidden_files_untouched:
        fail_reasons.append("observed_category_forbidden_paths_touched")
    if not diff_size_within_limit:
        fail_reasons.append("diff_size_limit_exceeded")
    if not required_tests_declared:
        fail_reasons.append("required_tests_not_declared")
    if not required_tests_executed:
        fail_reasons.append("required_tests_not_executed")
    if not required_tests_passed:
        fail_reasons.append("required_tests_not_passed")
    if not ci_green:
        fail_reasons.append("required_ci_checks_not_green")

    warnings: list[str] = []
    if runtime_semantics_changed:
        warnings.append("runtime_sensitive_paths_touched")
    if contract_shape_changed:
        warnings.append("contract_shape_related_paths_touched")
    if reviewer_fields_changed:
        warnings.append("reviewer_field_related_paths_touched")
    if not rollback_metadata_recorded:
        warnings.append("rollback_metadata_not_recorded")

    merge_eligible = len(fail_reasons) == 0

    return RubricEvaluationResult(
        declared_category=str(declared_category).strip(),
        observed_category=str(observed_category).strip(),
        allowed_files_only=allowed_files_only,
        forbidden_files_untouched=forbidden_files_untouched,
        diff_size_within_limit=diff_size_within_limit,
        required_tests_declared=bool(required_tests_declared),
        required_tests_executed=bool(required_tests_executed),
        required_tests_passed=bool(required_tests_passed),
        runtime_semantics_changed=runtime_semantics_changed,
        contract_shape_changed=contract_shape_changed,
        reviewer_fields_changed=reviewer_fields_changed,
        ci_required_checks_green=bool(ci_green),
        rollback_metadata_recorded=bool(rollback_metadata_recorded),
        merge_eligible=merge_eligible,
        fail_reasons=tuple(fail_reasons),
        warnings=tuple(warnings),
    )

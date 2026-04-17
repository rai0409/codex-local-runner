from __future__ import annotations

from fnmatch import fnmatch
from collections.abc import Mapping, Sequence
from typing import Any

from orchestrator.github_backend import build_github_progression_receipt
from orchestrator.policy_loader import load_merge_gate_policy
from orchestrator.schemas import MergeGateResult
from orchestrator.schemas import RubricEvaluationResult

REASON_DECLARED_OBSERVED_MISMATCH = "declared_category_does_not_match_observed_category"
REASON_CATEGORY_NOT_POLICY_ELIGIBLE = "category_not_policy_eligible"
REASON_FORBIDDEN_PATH_TOUCHED = "observed_category_forbidden_paths_touched"
REASON_DIFF_SIZE_LIMIT_EXCEEDED = "diff_size_limit_exceeded"
REASON_REQUIRED_TESTS_NOT_DECLARED = "required_tests_not_declared"
REASON_REQUIRED_TESTS_NOT_EXECUTED = "required_tests_not_executed"
REASON_REQUIRED_TESTS_NOT_PASSED = "required_tests_not_passed"
REASON_REQUIRED_CI_NOT_GREEN = "required_ci_checks_not_green"
REASON_CHANGED_FILES_MISSING = "changed_files_missing"
REASON_DIFF_STATS_MISSING = "diff_line_stats_missing"
REASON_CHANGED_FILES_COUNT_EXCEEDED = "changed_files_count_exceeded"
REASON_TOTAL_DIFF_LINES_EXCEEDED = "total_diff_lines_exceeded"
REASON_GENERATED_PATH_TOUCHED = "generated_path_touched"
REASON_BINARY_FILE_TOUCHED = "binary_file_touched"
REASON_RUNTIME_SENSITIVE_PATH_TOUCHED = "runtime_sensitive_paths_touched"
REASON_CONTRACT_SENSITIVE_PATH_TOUCHED = "contract_shape_related_paths_touched"
REASON_POLICY_CATEGORY_CONSTRAINTS_MISSING = "policy_category_constraints_missing"
REASON_CATEGORY_NOT_AUTO_MERGE_ALLOWED = "category_not_auto_merge_allowed"
_MERGE_BLOCKED_STATES = {"blocked", "behind", "dirty", "draft"}


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
            "runtime_sensitive_path_patterns": (),
            "contract_sensitive_path_patterns": (),
            "category_thresholds": {},
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

    def _optional_bool(value: Any) -> bool | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            if value in (0, 1):
                return bool(value)
            return None
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
        return None

    def _thresholds() -> dict[str, dict[str, Any]]:
        value = raw.get("category_thresholds", {})
        if not isinstance(value, Mapping):
            return {}
        result: dict[str, dict[str, Any]] = {}
        for category_name, category_raw in value.items():
            name = str(category_name).strip()
            if not name or not isinstance(category_raw, Mapping):
                continue

            def _int_from(category_key: str) -> int:
                raw_value = category_raw.get(category_key, 0)
                if isinstance(raw_value, bool):
                    return 0
                if isinstance(raw_value, int):
                    return max(raw_value, 0)
                if isinstance(raw_value, str):
                    text = raw_value.strip()
                    if text and text.isdigit():
                        return int(text)
                return 0

            def _tuple_from(category_key: str) -> tuple[str, ...]:
                raw_value = category_raw.get(category_key, ())
                if isinstance(raw_value, Sequence) and not isinstance(raw_value, (str, bytes)):
                    return tuple(str(item).strip() for item in raw_value if str(item).strip())
                return ()

            result[name] = {
                "max_changed_files": _int_from("max_changed_files"),
                "max_total_diff_lines": _int_from("max_total_diff_lines"),
                "forbidden_paths": _tuple_from("forbidden_paths"),
                "required_tests": _tuple_from("required_tests"),
                "requires_ci_green": _optional_bool(category_raw.get("requires_ci_green")),
            }
        return result

    return {
        "policy_eligible_categories": _tuple("policy_eligible_categories"),
        "auto_pr_candidate_categories": _tuple("auto_pr_candidate_categories"),
        "max_changed_files": _non_negative_int("max_changed_files"),
        "max_total_diff_lines": _non_negative_int("max_total_diff_lines"),
        "generated_path_patterns": _tuple("generated_path_patterns"),
        "binary_file_extensions": tuple(ext.lower() for ext in _tuple("binary_file_extensions")),
        "runtime_sensitive_path_patterns": _tuple("runtime_sensitive_path_patterns"),
        "contract_sensitive_path_patterns": _tuple("contract_sensitive_path_patterns"),
        "category_thresholds": _thresholds(),
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


def _is_forbidden_path(path: str, forbidden_patterns: tuple[str, ...]) -> bool:
    return any(fnmatch(path, pattern) for pattern in forbidden_patterns)


def _more_conservative_limit(global_limit: int, category_limit: int) -> int:
    positive_limits = [limit for limit in (global_limit, category_limit) if int(limit) > 0]
    if not positive_limits:
        return 0
    return min(positive_limits)


def _append_reason(reasons: list[str], reason: str) -> None:
    if reason and reason not in reasons:
        reasons.append(reason)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _derive_lifecycle_state(
    *,
    policy_eligible: bool,
    auto_pr_candidate: bool,
    github_progression: Mapping[str, Any] | None,
) -> str:
    if not policy_eligible:
        return "manual_only"
    if not auto_pr_candidate:
        return "policy_eligible"

    snapshot = _as_mapping(github_progression)
    if not bool(snapshot.get("state_available", False)):
        return "auto_pr_candidate"

    target = _as_mapping(snapshot.get("target"))
    if not _normalized_text(target.get("repository")) or not _normalized_text(target.get("target_ref")):
        return "auto_pr_candidate"

    checks = _as_mapping(snapshot.get("checks"))
    review = _as_mapping(snapshot.get("review"))
    mergeability = _as_mapping(snapshot.get("mergeability"))

    checks_state = _normalized_text(checks.get("state", "unknown")).lower() or "unknown"
    review_state = _normalized_text(review.get("state", "unknown")).lower() or "unknown"
    mergeability_state = _normalized_text(mergeability.get("state", "unknown")).lower() or "unknown"

    if review_state == "changes_requested" or mergeability_state in _MERGE_BLOCKED_STATES:
        return "merge_blocked"

    if checks_state == "pending":
        return "checks_pending"
    if checks_state != "passing":
        return "pr_preparable"

    if review_state != "approved":
        return "review_pending"
    if mergeability_state == "clean":
        return "approved_for_merge"
    return "checks_green"


def _derive_progression_policy(
    *,
    rubric: RubricEvaluationResult,
    changed_files: tuple[str, ...],
    additions: int,
    deletions: int,
    diff_line_stats_present: bool,
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
    category_thresholds = auto_progression["category_thresholds"]
    category_threshold = category_thresholds.get(observed_category)

    if declared_category != observed_category:
        _append_reason(reasons, REASON_DECLARED_OBSERVED_MISMATCH)
    if observed_category not in policy_categories:
        _append_reason(reasons, REASON_CATEGORY_NOT_POLICY_ELIGIBLE)
    elif not isinstance(category_threshold, Mapping):
        _append_reason(reasons, REASON_POLICY_CATEGORY_CONSTRAINTS_MISSING)

    if not rubric.forbidden_files_untouched:
        _append_reason(reasons, REASON_FORBIDDEN_PATH_TOUCHED)
    if not rubric.diff_size_within_limit:
        _append_reason(reasons, REASON_DIFF_SIZE_LIMIT_EXCEEDED)
    if not rubric.required_tests_declared:
        _append_reason(reasons, REASON_REQUIRED_TESTS_NOT_DECLARED)
    if not rubric.required_tests_executed:
        _append_reason(reasons, REASON_REQUIRED_TESTS_NOT_EXECUTED)
    if not rubric.required_tests_passed:
        _append_reason(reasons, REASON_REQUIRED_TESTS_NOT_PASSED)
    if not rubric.ci_required_checks_green:
        _append_reason(reasons, REASON_REQUIRED_CI_NOT_GREEN)

    if not changed_files:
        _append_reason(reasons, REASON_CHANGED_FILES_MISSING)
    if not diff_line_stats_present:
        _append_reason(reasons, REASON_DIFF_STATS_MISSING)

    category_max_changed_files = 0
    category_max_total_diff_lines = 0
    category_forbidden_paths: tuple[str, ...] = ()
    category_required_tests: tuple[str, ...] = ()
    category_requires_ci_green: bool | None = None
    if isinstance(category_threshold, Mapping):
        category_max_changed_files = int(category_threshold.get("max_changed_files", 0))
        category_max_total_diff_lines = int(category_threshold.get("max_total_diff_lines", 0))
        category_forbidden_paths = tuple(category_threshold.get("forbidden_paths", ()))
        category_required_tests = tuple(category_threshold.get("required_tests", ()))
        category_requires_ci_green = category_threshold.get("requires_ci_green")

    max_changed_files = _more_conservative_limit(
        int(auto_progression["max_changed_files"]),
        category_max_changed_files,
    )
    if max_changed_files > 0 and len(changed_files) > max_changed_files:
        _append_reason(reasons, REASON_CHANGED_FILES_COUNT_EXCEEDED)

    max_total_diff_lines = _more_conservative_limit(
        int(auto_progression["max_total_diff_lines"]),
        category_max_total_diff_lines,
    )
    if max_total_diff_lines > 0 and total_diff_lines > max_total_diff_lines:
        _append_reason(reasons, REASON_TOTAL_DIFF_LINES_EXCEEDED)

    if category_forbidden_paths and any(
        _is_forbidden_path(path, category_forbidden_paths) for path in changed_files
    ):
        _append_reason(reasons, REASON_FORBIDDEN_PATH_TOUCHED)

    if category_required_tests:
        if not rubric.required_tests_declared:
            _append_reason(reasons, REASON_REQUIRED_TESTS_NOT_DECLARED)
        if not rubric.required_tests_executed:
            _append_reason(reasons, REASON_REQUIRED_TESTS_NOT_EXECUTED)
        if not rubric.required_tests_passed:
            _append_reason(reasons, REASON_REQUIRED_TESTS_NOT_PASSED)

    if category_requires_ci_green is True and not rubric.ci_required_checks_green:
        _append_reason(reasons, REASON_REQUIRED_CI_NOT_GREEN)

    generated_patterns = tuple(auto_progression["generated_path_patterns"])
    if generated_patterns and any(_is_generated_path(path, generated_patterns) for path in changed_files):
        _append_reason(reasons, REASON_GENERATED_PATH_TOUCHED)

    binary_extensions = tuple(auto_progression["binary_file_extensions"])
    if binary_extensions and any(_is_binary_path(path, binary_extensions) for path in changed_files):
        _append_reason(reasons, REASON_BINARY_FILE_TOUCHED)

    runtime_sensitive_patterns = tuple(auto_progression["runtime_sensitive_path_patterns"])
    if runtime_sensitive_patterns and any(
        _is_generated_path(path, runtime_sensitive_patterns) for path in changed_files
    ):
        _append_reason(reasons, REASON_RUNTIME_SENSITIVE_PATH_TOUCHED)

    contract_sensitive_patterns = tuple(auto_progression["contract_sensitive_path_patterns"])
    if contract_sensitive_patterns and any(
        _is_generated_path(path, contract_sensitive_patterns) for path in changed_files
    ):
        _append_reason(reasons, REASON_CONTRACT_SENSITIVE_PATH_TOUCHED)

    if reasons:
        return "manual_only", False, False, tuple(reasons)

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
    diff_line_stats_present: bool = True,
    github_signals: Mapping[str, Any] | None = None,
) -> MergeGateResult:
    effective_policy = policy if policy is not None else load_merge_gate_policy()
    fail_reasons: list[str] = []

    if _policy_bool(effective_policy, "require_rubric_all_pass", True) and not rubric.merge_eligible:
        if rubric.fail_reasons:
            fail_reasons.extend(rubric.fail_reasons)
        else:
            fail_reasons.append("rubric_not_all_pass")

    if _policy_bool(effective_policy, "require_ci_green", True) and not rubric.ci_required_checks_green:
        fail_reasons.append(REASON_REQUIRED_CI_NOT_GREEN)

    if _policy_bool(effective_policy, "require_declared_equals_observed_category", True):
        if rubric.declared_category != rubric.observed_category:
            fail_reasons.append(REASON_DECLARED_OBSERVED_MISMATCH)

    if _policy_bool(effective_policy, "require_no_forbidden_paths_touched", True):
        if not rubric.forbidden_files_untouched:
            fail_reasons.append(REASON_FORBIDDEN_PATH_TOUCHED)

    if _policy_bool(effective_policy, "require_diff_size_within_limit", True):
        if not rubric.diff_size_within_limit:
            fail_reasons.append(REASON_DIFF_SIZE_LIMIT_EXCEEDED)

    auto_merge_categories = _policy_categories(effective_policy)
    auto_merge_allowed = rubric.observed_category in auto_merge_categories
    if not auto_merge_allowed:
        fail_reasons.append(REASON_CATEGORY_NOT_AUTO_MERGE_ALLOWED)

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
            diff_line_stats_present=diff_line_stats_present,
            policy=effective_policy,
        )
    )
    github_progression = build_github_progression_receipt(
        github_signals=github_signals,
        progression_state=progression_state,
        policy_eligible=policy_eligible,
        auto_pr_candidate=auto_pr_candidate,
    )
    lifecycle_state = _derive_lifecycle_state(
        policy_eligible=policy_eligible,
        auto_pr_candidate=auto_pr_candidate,
        github_progression=github_progression,
    )
    return MergeGateResult(
        passed=passed,
        fail_reasons=tuple(deduped),
        auto_merge_allowed=auto_merge_allowed,
        progression_state=progression_state,
        policy_eligible=policy_eligible,
        auto_pr_candidate=auto_pr_candidate,
        lifecycle_state=lifecycle_state,
        progression_fail_reasons=progression_fail_reasons,
        github_progression=github_progression,
    )

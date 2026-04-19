from __future__ import annotations

from collections.abc import Mapping
from typing import Any


DIMENSION_MAX = {
    "correctness": 4.0,
    "scope_control": 2.0,
    "safety": 2.5,
    "repo_alignment": 1.5,
}


def _as_optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes"}:
            return True
        if normalized in {"0", "false", "no"}:
            return False
    return None


def _as_normalized_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.lstrip("-").isdigit():
            return int(text)
    return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return round(min(max(value, minimum), maximum), 2)


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def score_review_facts(facts: Mapping[str, Any]) -> dict[str, Any]:
    failure_codes: list[str] = []
    decision_basis: list[str] = []

    execution_status = _as_normalized_text(facts.get("execution_status"))
    verify_status = _as_normalized_text(facts.get("verify_status"))
    accepted_status = _as_normalized_text(facts.get("accepted_status"))
    declared_category = _as_normalized_text(facts.get("declared_category"))
    observed_category = _as_normalized_text(facts.get("observed_category"))

    forbidden_files_untouched = _as_optional_bool(facts.get("forbidden_files_untouched"))
    diff_size_within_limit = _as_optional_bool(facts.get("diff_size_within_limit"))
    runtime_semantics_changed = _as_optional_bool(facts.get("runtime_semantics_changed"))
    contract_shape_changed = _as_optional_bool(facts.get("contract_shape_changed"))
    reviewer_fields_changed = _as_optional_bool(facts.get("reviewer_fields_changed"))
    merge_gate_passed = _as_optional_bool(facts.get("merge_gate_passed"))
    required_tests_declared = _as_optional_bool(facts.get("required_tests_declared"))
    required_tests_executed = _as_optional_bool(facts.get("required_tests_executed"))
    required_tests_passed = _as_optional_bool(facts.get("required_tests_passed"))
    prompt_contract_compliant = _as_optional_bool(facts.get("prompt_contract_compliant"))

    rubric_fail_reasons = _as_string_list(facts.get("rubric_fail_reasons"))
    merge_gate_fail_reasons = _as_string_list(facts.get("merge_gate_fail_reasons"))
    rubric_warnings = _as_string_list(facts.get("rubric_warnings"))

    additions = _as_int(facts.get("additions"))
    deletions = _as_int(facts.get("deletions"))
    changed_files = _as_string_list(facts.get("changed_files"))
    total_diff_lines = (additions or 0) + (deletions or 0)

    correctness = DIMENSION_MAX["correctness"]
    scope_control = DIMENSION_MAX["scope_control"]
    safety = DIMENSION_MAX["safety"]
    repo_alignment = DIMENSION_MAX["repo_alignment"]

    if accepted_status != "accepted":
        correctness -= 0.8
        repo_alignment -= 0.7
        _append_unique(decision_basis, "accepted_status_not_accepted")

    if execution_status == "completed":
        _append_unique(decision_basis, "execution_completed")
    elif execution_status:
        correctness -= 1.8
        _append_unique(decision_basis, f"execution_status:{execution_status}")
    else:
        correctness -= 2.4
        repo_alignment -= 0.2
        _append_unique(decision_basis, "execution_status_missing")
        _append_unique(failure_codes, "contract_drift")

    if verify_status == "passed":
        _append_unique(decision_basis, "validation_passed")
    elif verify_status == "failed":
        correctness -= 1.6
        _append_unique(decision_basis, "validation_failed")
        _append_unique(failure_codes, "insufficient_tests")
    elif verify_status == "not_run":
        correctness -= 2.1
        _append_unique(decision_basis, "validation_not_run")
        _append_unique(failure_codes, "insufficient_tests")
    else:
        correctness -= 2.3
        _append_unique(decision_basis, "validation_status_missing_or_unrecognized")
        _append_unique(failure_codes, "insufficient_tests")

    if required_tests_declared is False:
        correctness -= 0.3
        _append_unique(decision_basis, "required_tests_not_declared")
        _append_unique(failure_codes, "insufficient_tests")
    elif required_tests_declared is None:
        correctness -= 0.2
        _append_unique(decision_basis, "required_tests_declared_unknown")
        _append_unique(failure_codes, "insufficient_tests")

    if required_tests_executed is False:
        correctness -= 0.3
        _append_unique(decision_basis, "required_tests_not_executed")
        _append_unique(failure_codes, "insufficient_tests")
    elif required_tests_executed is None:
        correctness -= 0.2
        _append_unique(decision_basis, "required_tests_executed_unknown")
        _append_unique(failure_codes, "insufficient_tests")

    if required_tests_passed is False:
        correctness -= 0.4
        _append_unique(decision_basis, "required_tests_not_passed")
        _append_unique(failure_codes, "insufficient_tests")
    elif required_tests_passed is None:
        correctness -= 0.2
        _append_unique(decision_basis, "required_tests_passed_unknown")
        _append_unique(failure_codes, "insufficient_tests")

    if forbidden_files_untouched is False:
        scope_control -= 1.2
        _append_unique(decision_basis, "forbidden_paths_touched")
        _append_unique(failure_codes, "touched_forbidden_file")
    elif forbidden_files_untouched is None:
        scope_control -= 0.3
        _append_unique(decision_basis, "forbidden_path_signal_missing")

    if diff_size_within_limit is False:
        scope_control -= 0.8
        _append_unique(decision_basis, "diff_size_limit_exceeded")
        _append_unique(failure_codes, "scope_explosion")
    elif diff_size_within_limit is None:
        scope_control -= 0.3
        _append_unique(decision_basis, "diff_size_signal_missing")

    if total_diff_lines > 600:
        scope_control -= 0.4
        _append_unique(decision_basis, "diff_lines_above_600")
        _append_unique(failure_codes, "scope_explosion")

    if len(changed_files) > 60:
        scope_control -= 0.3
        _append_unique(decision_basis, "changed_files_above_60")
        _append_unique(failure_codes, "scope_explosion")
    elif not changed_files:
        scope_control -= 0.2
        _append_unique(decision_basis, "changed_files_missing_or_empty")

    if runtime_semantics_changed is True:
        safety -= 1.0
        _append_unique(decision_basis, "runtime_semantics_changed")
        _append_unique(failure_codes, "hidden_runtime_semantics")
    elif runtime_semantics_changed is None:
        safety -= 0.2
        _append_unique(decision_basis, "runtime_semantics_signal_missing")

    if contract_shape_changed is True:
        safety -= 0.8
        _append_unique(decision_basis, "contract_shape_changed")
        _append_unique(failure_codes, "contract_drift")
        _append_unique(failure_codes, "weak_backward_compat")
    elif contract_shape_changed is None:
        safety -= 0.2
        _append_unique(decision_basis, "contract_shape_signal_missing")

    if reviewer_fields_changed is True:
        safety -= 0.4
        _append_unique(decision_basis, "reviewer_fields_changed")
        _append_unique(failure_codes, "weak_backward_compat")
    elif reviewer_fields_changed is None:
        safety -= 0.1
        _append_unique(decision_basis, "reviewer_fields_signal_missing")

    if declared_category and observed_category and declared_category != observed_category:
        repo_alignment -= 0.5
        _append_unique(decision_basis, "declared_observed_category_mismatch")
        _append_unique(failure_codes, "contract_drift")
    elif not declared_category or not observed_category:
        repo_alignment -= 0.3
        _append_unique(decision_basis, "category_signal_missing")
        _append_unique(failure_codes, "contract_drift")

    if merge_gate_passed is False:
        repo_alignment -= 0.3
        _append_unique(decision_basis, "merge_gate_not_passed")
    elif merge_gate_passed is None:
        repo_alignment -= 0.2
        _append_unique(decision_basis, "merge_gate_signal_missing")

    if prompt_contract_compliant is False:
        repo_alignment -= 0.6
        _append_unique(decision_basis, "prompt_contract_noncompliant")
        _append_unique(failure_codes, "prompt_noncompliance")
    elif prompt_contract_compliant is None:
        repo_alignment -= 0.3
        _append_unique(decision_basis, "prompt_contract_signal_missing")

    reason_to_code = {
        "observed_category_forbidden_paths_touched": "touched_forbidden_file",
        "diff_size_limit_exceeded": "scope_explosion",
        "required_tests_not_declared": "insufficient_tests",
        "required_tests_not_executed": "insufficient_tests",
        "required_tests_not_passed": "insufficient_tests",
        "declared_category_does_not_match_observed_category": "contract_drift",
        "runtime_sensitive_paths_touched": "hidden_runtime_semantics",
        "contract_shape_related_paths_touched": "weak_backward_compat",
        "reviewer_field_related_paths_touched": "weak_backward_compat",
    }
    for reason in [*rubric_fail_reasons, *merge_gate_fail_reasons, *rubric_warnings]:
        mapped = reason_to_code.get(reason)
        if mapped is not None:
            _append_unique(failure_codes, mapped)
            _append_unique(decision_basis, reason)

    dimension_scores = {
        "correctness": _clamp(correctness, 0.0, DIMENSION_MAX["correctness"]),
        "scope_control": _clamp(scope_control, 0.0, DIMENSION_MAX["scope_control"]),
        "safety": _clamp(safety, 0.0, DIMENSION_MAX["safety"]),
        "repo_alignment": _clamp(repo_alignment, 0.0, DIMENSION_MAX["repo_alignment"]),
    }
    score_total = _clamp(
        dimension_scores["correctness"]
        + dimension_scores["scope_control"]
        + dimension_scores["safety"]
        + dimension_scores["repo_alignment"],
        0.0,
        10.0,
    )

    return {
        "score_total": score_total,
        "dimension_scores": dimension_scores,
        "failure_codes": failure_codes,
        "decision_basis": decision_basis,
    }

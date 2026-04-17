from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CategoryClassificationResult:
    declared_category: str
    observed_category: str
    declared_category_supported: bool
    declared_matches_observed: bool
    changed_files: tuple[str, ...]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class RubricEvaluationResult:
    declared_category: str
    observed_category: str
    allowed_files_only: bool
    forbidden_files_untouched: bool
    diff_size_within_limit: bool
    required_tests_declared: bool
    required_tests_executed: bool
    required_tests_passed: bool
    runtime_semantics_changed: bool
    contract_shape_changed: bool
    reviewer_fields_changed: bool
    ci_required_checks_green: bool
    rollback_metadata_recorded: bool
    merge_eligible: bool
    fail_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MergeGateResult:
    passed: bool
    fail_reasons: tuple[str, ...]
    auto_merge_allowed: bool
    progression_state: str
    policy_eligible: bool
    auto_pr_candidate: bool
    lifecycle_state: str = "manual_only"
    write_authority: dict[str, Any] | None = None
    progression_fail_reasons: tuple[str, ...] = ()
    github_progression: dict[str, Any] | None = None
    replan_input: dict[str, Any] | None = None

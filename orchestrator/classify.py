from __future__ import annotations

from collections.abc import Mapping
from typing import Iterable

from orchestrator.policy_loader import get_change_category_names
from orchestrator.schemas import CategoryClassificationResult

_RUNTIME_SENSITIVE_EXACT = {"run_codex.py", "app.py"}
_RUNTIME_SENSITIVE_PREFIXES = ("adapters/", "verify/", "workspace/")


def _normalize_paths(changed_files: Iterable[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw in changed_files:
        path = str(raw).strip().replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        if path:
            normalized.append(path)
    return tuple(sorted(set(normalized)))


def _is_docs_path(path: str) -> bool:
    return path.startswith("docs/")


def _is_ci_path(path: str) -> bool:
    return path.startswith(".github/workflows/")


def _is_test_path(path: str) -> bool:
    return path.startswith("tests/")


def _is_runtime_sensitive(path: str) -> bool:
    if path in _RUNTIME_SENSITIVE_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in _RUNTIME_SENSITIVE_PREFIXES)


def infer_observed_category(changed_files: Iterable[str]) -> str:
    paths = _normalize_paths(changed_files)
    if not paths:
        return "feature"

    if all(_is_docs_path(path) for path in paths):
        return "docs_only"

    if all(_is_ci_path(path) for path in paths):
        return "ci_only"

    if all(_is_test_path(path) for path in paths):
        return "test_only"

    docs_or_tests_only = all(_is_docs_path(path) or _is_test_path(path) for path in paths)
    has_docs = any(_is_docs_path(path) for path in paths)
    has_tests = any(_is_test_path(path) for path in paths)
    if docs_or_tests_only and has_docs and has_tests:
        return "contract_guard_only"

    if any(_is_runtime_sensitive(path) for path in paths):
        return "runtime_fix_high_risk"

    return "feature"


def validate_declared_category(
    declared_category: str,
    changed_files: Iterable[str],
    *,
    change_categories_policy: Mapping[str, object] | None = None,
) -> tuple[bool, str]:
    declared = str(declared_category).strip()
    category_names = set(
        get_change_category_names(change_categories_policy=change_categories_policy)
    )
    if declared not in category_names:
        return False, "declared_category_unsupported"

    observed = infer_observed_category(changed_files)
    if declared != observed:
        return False, f"declared_category_mismatch_observed:{observed}"

    return True, ""


def classify_changes(
    *,
    declared_category: str,
    changed_files: Iterable[str],
    change_categories_policy: Mapping[str, object] | None = None,
) -> CategoryClassificationResult:
    declared = str(declared_category).strip()
    paths = _normalize_paths(changed_files)
    observed = infer_observed_category(paths)
    category_names = set(
        get_change_category_names(change_categories_policy=change_categories_policy)
    )

    reasons: list[str] = []
    declared_supported = declared in category_names
    declared_matches_observed = declared_supported and declared == observed

    if not declared_supported:
        reasons.append("declared_category_unsupported")
    elif not declared_matches_observed:
        reasons.append(f"declared_category_mismatch_observed:{observed}")

    if observed == "runtime_fix_high_risk":
        reasons.append("runtime_sensitive_paths_touched")

    return CategoryClassificationResult(
        declared_category=declared,
        observed_category=observed,
        declared_category_supported=declared_supported,
        declared_matches_observed=declared_matches_observed,
        changed_files=paths,
        reasons=tuple(reasons),
    )

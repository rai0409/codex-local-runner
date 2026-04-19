from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

CHANGE_CATEGORIES_PATH = "config/change_categories.yaml"
MERGE_GATE_PATH = "config/merge_gate.yaml"


def _as_mapping(value: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping")
    return value


def _as_string(value: Any, *, context: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{context} must be a non-empty string")
    return text


def _as_string_tuple(value: Any, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
    return tuple(result)


def _as_non_negative_int(value: Any, *, context: str, default: int) -> int:
    if value is None:
        return int(default)
    if isinstance(value, bool):
        raise ValueError(f"{context} must be an integer")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"{context} must be non-negative")
        return value
    if isinstance(value, str):
        text = value.strip()
        if text and text.isdigit():
            return int(text)
    raise ValueError(f"{context} must be a non-negative integer")


def _as_optional_bool(value: Any, *, context: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise ValueError(f"{context} must be a boolean")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    raise ValueError(f"{context} must be a boolean")


def _as_progression_category_thresholds(
    value: Any,
    *,
    context: str,
) -> dict[str, Any]:
    if value is None:
        return {}
    raw = _as_mapping(value, context=context)
    result: dict[str, Any] = {}
    for category_name, category_raw in raw.items():
        name = _as_string(category_name, context=f"{context}.category")
        body = _as_mapping(category_raw, context=f"{context}.{name}")
        result[name] = {
            "max_changed_files": _as_non_negative_int(
                body.get("max_changed_files"),
                context=f"{context}.{name}.max_changed_files",
                default=0,
            ),
            "max_total_diff_lines": _as_non_negative_int(
                body.get("max_total_diff_lines"),
                context=f"{context}.{name}.max_total_diff_lines",
                default=0,
            ),
            "forbidden_paths": _as_string_tuple(
                body.get("forbidden_paths", []),
                context=f"{context}.{name}.forbidden_paths",
            ),
            "required_tests": _as_string_tuple(
                body.get("required_tests", []),
                context=f"{context}.{name}.required_tests",
            ),
            "requires_ci_green": _as_optional_bool(
                body.get("requires_ci_green"),
                context=f"{context}.{name}.requires_ci_green",
            ),
        }
    return result


def _load_yaml_policy_file(path: str, *, context: str) -> Mapping[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"{context}: YAML parsing support is required to load '{path}', "
            "but 'yaml' is not available in the runtime environment."
        ) from exc

    loaded = yaml.safe_load(text)
    return _as_mapping(loaded, context=context)


@lru_cache(maxsize=1)
def load_change_categories_policy(path: str = CHANGE_CATEGORIES_PATH) -> dict[str, Any]:
    raw = _load_yaml_policy_file(path, context="change_categories policy")
    categories_raw = _as_mapping(raw.get("categories"), context="change_categories.categories")

    categories: dict[str, Any] = {}
    for category_name, category_raw in categories_raw.items():
        name = _as_string(category_name, context="category name")
        body = _as_mapping(category_raw, context=f"category {name}")
        categories[name] = {
            "description": _as_string(body.get("description", ""), context=f"{name}.description"),
            "allowed_paths": _as_string_tuple(
                body.get("allowed_paths", []),
                context=f"{name}.allowed_paths",
            ),
            "forbidden_paths": _as_string_tuple(
                body.get("forbidden_paths", []),
                context=f"{name}.forbidden_paths",
            ),
            "required_tests": _as_string_tuple(
                body.get("required_tests", []),
                context=f"{name}.required_tests",
            ),
            "auto_merge_allowed": bool(body.get("auto_merge_allowed", False)),
        }

    return {"categories": categories}


def get_change_category_names(
    *,
    change_categories_policy: Mapping[str, Any] | None = None,
) -> tuple[str, ...]:
    policy = change_categories_policy or load_change_categories_policy()
    categories = _as_mapping(policy.get("categories"), context="change_categories.categories")
    return tuple(str(name).strip() for name in categories.keys() if str(name).strip())


def get_change_category_policy(
    category_name: str,
    *,
    change_categories_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    name = str(category_name).strip()
    if not name:
        return None

    policy = change_categories_policy or load_change_categories_policy()
    categories = _as_mapping(policy.get("categories"), context="change_categories.categories")
    raw = categories.get(name)
    if raw is None:
        return None
    return dict(_as_mapping(raw, context=f"category {name}"))


@lru_cache(maxsize=1)
def load_merge_gate_policy(path: str = MERGE_GATE_PATH) -> dict[str, Any]:
    raw = _load_yaml_policy_file(path, context="merge_gate policy")
    auto_progression_raw = _as_mapping(
        raw.get("auto_progression", {}),
        context="merge_gate.auto_progression",
    )
    write_authority_raw = _as_mapping(
        raw.get("write_authority", {}),
        context="merge_gate.write_authority",
    )
    retry_replan_raw = _as_mapping(
        raw.get("retry_replan", {}),
        context="merge_gate.retry_replan",
    )
    policy_eligible_categories = _as_string_tuple(
        auto_progression_raw.get("policy_eligible_categories", []),
        context="merge_gate.auto_progression.policy_eligible_categories",
    )
    auto_pr_candidate_categories = _as_string_tuple(
        auto_progression_raw.get("auto_pr_candidate_categories", []),
        context="merge_gate.auto_progression.auto_pr_candidate_categories",
    )
    write_allowed_categories = _as_string_tuple(
        write_authority_raw.get("allowed_categories", ["docs_only"]),
        context="merge_gate.write_authority.allowed_categories",
    )
    write_required_lifecycle_states = _as_string_tuple(
        write_authority_raw.get("required_lifecycle_states", ["approved_for_merge"]),
        context="merge_gate.write_authority.required_lifecycle_states",
    )
    retry_retriable_failure_types = _as_string_tuple(
        retry_replan_raw.get("retriable_failure_types", ["execution_failure", "missing_signal"]),
        context="merge_gate.retry_replan.retriable_failure_types",
    )
    return {
        "require_ci_green": bool(raw.get("require_ci_green", True)),
        "require_rubric_all_pass": bool(raw.get("require_rubric_all_pass", True)),
        "require_declared_equals_observed_category": bool(
            raw.get("require_declared_equals_observed_category", True)
        ),
        "require_no_forbidden_paths_touched": bool(
            raw.get("require_no_forbidden_paths_touched", True)
        ),
        "require_diff_size_within_limit": bool(raw.get("require_diff_size_within_limit", True)),
        "auto_merge_categories": _as_string_tuple(
            raw.get("auto_merge_categories", []),
            context="merge_gate.auto_merge_categories",
        ),
        "auto_progression": {
            "policy_eligible_categories": policy_eligible_categories,
            "auto_pr_candidate_categories": auto_pr_candidate_categories,
            "max_changed_files": _as_non_negative_int(
                auto_progression_raw.get("max_changed_files"),
                context="merge_gate.auto_progression.max_changed_files",
                default=0,
            ),
            "max_total_diff_lines": _as_non_negative_int(
                auto_progression_raw.get("max_total_diff_lines"),
                context="merge_gate.auto_progression.max_total_diff_lines",
                default=0,
            ),
            "generated_path_patterns": _as_string_tuple(
                auto_progression_raw.get("generated_path_patterns", []),
                context="merge_gate.auto_progression.generated_path_patterns",
            ),
            "binary_file_extensions": _as_string_tuple(
                auto_progression_raw.get("binary_file_extensions", []),
                context="merge_gate.auto_progression.binary_file_extensions",
            ),
            "runtime_sensitive_path_patterns": _as_string_tuple(
                auto_progression_raw.get("runtime_sensitive_path_patterns", []),
                context="merge_gate.auto_progression.runtime_sensitive_path_patterns",
            ),
            "contract_sensitive_path_patterns": _as_string_tuple(
                auto_progression_raw.get("contract_sensitive_path_patterns", []),
                context="merge_gate.auto_progression.contract_sensitive_path_patterns",
            ),
            "category_thresholds": _as_progression_category_thresholds(
                auto_progression_raw.get("category_thresholds"),
                context="merge_gate.auto_progression.category_thresholds",
            ),
        },
        "write_authority": {
            "enabled": bool(write_authority_raw.get("enabled", False)),
            "dry_run": bool(write_authority_raw.get("dry_run", True)),
            "kill_switch": bool(write_authority_raw.get("kill_switch", True)),
            "allowed_categories": (
                write_allowed_categories if write_allowed_categories else ("docs_only",)
            ),
            "required_lifecycle_states": (
                write_required_lifecycle_states
                if write_required_lifecycle_states
                else ("approved_for_merge",)
            ),
        },
        "retry_replan": {
            "max_attempts": _as_non_negative_int(
                retry_replan_raw.get("max_attempts"),
                context="merge_gate.retry_replan.max_attempts",
                default=2,
            ),
            "retriable_failure_types": (
                retry_retriable_failure_types
                if retry_retriable_failure_types
                else ("execution_failure", "missing_signal")
            ),
        },
    }

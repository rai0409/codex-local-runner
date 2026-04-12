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
    }

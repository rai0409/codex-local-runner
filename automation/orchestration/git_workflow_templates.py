from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


_DEFAULT_GIT_WORKFLOW_POLICY: dict[str, Any] = {
    "version": 1,
    "branch": {
        "prefixes": ["pr", "fix", "ops", "runtime", "approval"],
        "separator": "-",
        "max_length": 64,
    },
    "commit": {
        "subject": {
            "imperative": True,
            "max_length": 72,
            "allow_component_prefix": True,
            "trailing_period": False,
        }
    },
    "pr": {
        "title": {
            "prefix_style": "bracketed_component",
            "max_length": 72,
        },
        "body": {
            "sections": [
                "Summary",
                "What changed",
                "Validation",
                "Scope notes",
            ]
        },
    },
    "cleanup": {
        "sync_main_first": True,
        "delete_local_branch": True,
        "delete_remote_branch_optional": True,
        "fetch_prune_before_cleanup": True,
    },
}

_DEFAULT_SEPARATOR = "-"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _policy_path() -> Path:
    return _repo_root() / "config" / "git_workflow_policy.yaml"


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return " ".join(text.strip().split())


def _truncate(text: str, *, max_length: int) -> str:
    if max_length <= 0:
        return ""
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3].rstrip() + "..."


def _load_git_workflow_policy() -> dict[str, Any]:
    payload: dict[str, Any] = dict(_DEFAULT_GIT_WORKFLOW_POLICY)
    path = _policy_path()
    if not path.exists():
        return payload
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return payload
    if not isinstance(loaded, Mapping):
        return payload
    for key in ("branch", "commit", "pr", "cleanup"):
        default_value = payload.get(key)
        loaded_value = loaded.get(key)
        if isinstance(default_value, Mapping) and isinstance(loaded_value, Mapping):
            merged = dict(default_value)
            for sub_key, sub_value in loaded_value.items():
                if isinstance(merged.get(sub_key), Mapping) and isinstance(sub_value, Mapping):
                    nested = dict(merged[sub_key])
                    nested.update(sub_value)
                    merged[sub_key] = nested
                else:
                    merged[sub_key] = sub_value
            payload[key] = merged
    if "version" in loaded:
        payload["version"] = loaded.get("version")
    return payload


def _normalize_component(value: Any) -> str:
    text = _coerce_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", _DEFAULT_SEPARATOR, text)
    text = re.sub(rf"{re.escape(_DEFAULT_SEPARATOR)}+", _DEFAULT_SEPARATOR, text)
    return text.strip(_DEFAULT_SEPARATOR)


def normalize_branch_slug(slug: Any, *, separator: str = _DEFAULT_SEPARATOR, max_length: int = 48) -> str:
    text = _coerce_text(slug).lower()
    text = re.sub(r"[^a-z0-9]+", separator, text)
    text = re.sub(rf"{re.escape(separator)}+", separator, text)
    text = text.strip(separator)
    if not text:
        text = "update"
    return _truncate(text, max_length=max_length).strip(separator) or "update"


def render_branch_name(
    *,
    prefix: Any,
    slug: Any,
    issue_id: Any | None = None,
    policy: Mapping[str, Any] | None = None,
) -> str:
    loaded_policy = dict(policy or _load_git_workflow_policy())
    branch_policy = loaded_policy.get("branch") if isinstance(loaded_policy, Mapping) else {}
    if not isinstance(branch_policy, Mapping):
        branch_policy = {}

    configured_prefixes = branch_policy.get("prefixes")
    allowed_prefixes = tuple(
        _normalize_component(item) for item in configured_prefixes if _normalize_component(item)
    ) if isinstance(configured_prefixes, Sequence) and not isinstance(configured_prefixes, (str, bytes)) else (
        "pr",
        "fix",
        "ops",
        "runtime",
        "approval",
    )
    separator = str(branch_policy.get("separator") or _DEFAULT_SEPARATOR)
    max_length = int(branch_policy.get("max_length") or 64)

    normalized_prefix = _normalize_component(prefix) or (allowed_prefixes[0] if allowed_prefixes else "pr")
    if normalized_prefix not in allowed_prefixes:
        normalized_prefix = allowed_prefixes[0] if allowed_prefixes else "pr"

    parts = [normalized_prefix, normalize_branch_slug(slug, separator=separator, max_length=max_length)]
    issue_token = normalize_branch_slug(issue_id, separator=separator, max_length=20) if issue_id else ""
    if issue_token:
        parts.append(issue_token)

    branch_name = separator.join(part for part in parts if part)
    if len(branch_name) <= max_length:
        return branch_name

    prefix_head = f"{normalized_prefix}{separator}"
    remaining = max(max_length - len(prefix_head), 1)
    suffix = normalize_branch_slug(separator.join(parts[1:]), separator=separator, max_length=remaining)
    return (prefix_head + suffix).strip(separator) or normalized_prefix


def render_commit_subject(
    *,
    summary: Any,
    component: Any | None = None,
    policy: Mapping[str, Any] | None = None,
) -> str:
    loaded_policy = dict(policy or _load_git_workflow_policy())
    commit_policy = loaded_policy.get("commit") if isinstance(loaded_policy, Mapping) else {}
    if not isinstance(commit_policy, Mapping):
        commit_policy = {}
    subject_policy = commit_policy.get("subject")
    if not isinstance(subject_policy, Mapping):
        subject_policy = {}

    max_length = int(subject_policy.get("max_length") or 72)
    allow_component_prefix = bool(subject_policy.get("allow_component_prefix", True))
    trailing_period = bool(subject_policy.get("trailing_period", False))

    subject_text = _coerce_text(summary) or "Update workflow artifacts"
    if not trailing_period:
        subject_text = subject_text.rstrip(".")

    normalized_component = _normalize_component(component)
    if allow_component_prefix and normalized_component:
        subject_text = f"{normalized_component}: {subject_text}"

    return _truncate(subject_text, max_length=max_length)


def render_commit_message(
    *,
    summary: Any,
    component: Any | None = None,
    body_lines: Sequence[Any] | None = None,
    footer_lines: Sequence[Any] | None = None,
    policy: Mapping[str, Any] | None = None,
) -> str:
    subject = render_commit_subject(summary=summary, component=component, policy=policy)
    lines: list[str] = [subject]

    normalized_body = [_coerce_text(item) for item in (body_lines or [])]
    normalized_body = [item for item in normalized_body if item]
    normalized_footer = [_coerce_text(item) for item in (footer_lines or [])]
    normalized_footer = [item for item in normalized_footer if item]

    if normalized_body:
        lines.extend(["", *normalized_body])
    if normalized_footer:
        lines.extend(["", *normalized_footer])
    return "\n".join(lines)


def render_cleanup_steps(policy: Mapping[str, Any] | None = None) -> tuple[str, ...]:
    loaded_policy = dict(policy or _load_git_workflow_policy())
    cleanup_policy = loaded_policy.get("cleanup") if isinstance(loaded_policy, Mapping) else {}
    if not isinstance(cleanup_policy, Mapping):
        cleanup_policy = {}

    steps: list[str] = []
    if bool(cleanup_policy.get("fetch_prune_before_cleanup", True)):
        steps.append("git fetch --prune")
    if bool(cleanup_policy.get("sync_main_first", True)):
        steps.extend(["git checkout main", "git pull --ff-only"])
    if bool(cleanup_policy.get("delete_local_branch", True)):
        steps.append("git branch -d <branch>")
    if bool(cleanup_policy.get("delete_remote_branch_optional", True)):
        steps.append("git push origin --delete <branch>  # optional")
    return tuple(steps)


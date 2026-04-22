from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


_DEFAULT_POLICY: dict[str, Any] = {
    "version": 1,
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
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _policy_path() -> Path:
    return _repo_root() / "config" / "git_workflow_policy.yaml"


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _truncate(text: str, *, max_length: int) -> str:
    if max_length <= 0:
        return ""
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3].rstrip() + "..."


def _to_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [_coerce_text(item) for item in value.splitlines()]
        compact = [item for item in parts if item]
        return compact if compact else [_coerce_text(value)] if _coerce_text(value) else []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        lines = [_coerce_text(item) for item in value]
        return [item for item in lines if item]
    text = _coerce_text(value)
    return [text] if text else []


def _normalize_component(value: Any) -> str:
    text = _coerce_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _load_policy() -> dict[str, Any]:
    payload: dict[str, Any] = dict(_DEFAULT_POLICY)
    path = _policy_path()
    if not path.exists():
        return payload
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return payload
    if not isinstance(loaded, Mapping):
        return payload

    pr_default = payload.get("pr")
    pr_loaded = loaded.get("pr")
    if isinstance(pr_default, Mapping) and isinstance(pr_loaded, Mapping):
        merged = dict(pr_default)
        for key, value in pr_loaded.items():
            if isinstance(merged.get(key), Mapping) and isinstance(value, Mapping):
                nested = dict(merged[key])
                nested.update(value)
                merged[key] = nested
            else:
                merged[key] = value
        payload["pr"] = merged
    if "version" in loaded:
        payload["version"] = loaded.get("version")
    return payload


def _render_list_block(header: str, lines: Sequence[str]) -> str:
    normalized_lines = [_coerce_text(item) for item in lines if _coerce_text(item)]
    if not normalized_lines:
        normalized_lines = ["n/a"]
    bullets = [f"- {_truncate(item, max_length=160)}" for item in normalized_lines]
    return "\n".join([f"## {header}", *bullets])


def render_pr_title(
    *,
    summary: Any,
    scope: Any | None = None,
    policy: Mapping[str, Any] | None = None,
) -> str:
    loaded_policy = dict(policy or _load_policy())
    pr_policy = loaded_policy.get("pr") if isinstance(loaded_policy, Mapping) else {}
    if not isinstance(pr_policy, Mapping):
        pr_policy = {}
    title_policy = pr_policy.get("title")
    if not isinstance(title_policy, Mapping):
        title_policy = {}

    max_length = int(title_policy.get("max_length") or 72)
    prefix_style = _coerce_text(title_policy.get("prefix_style")).lower() or "bracketed_component"

    summary_text = _coerce_text(summary) or "Update workflow artifacts"
    component = _normalize_component(scope)

    if component and prefix_style == "bracketed_component":
        title = f"[{component}] {summary_text}"
    elif component and prefix_style == "plain_component":
        title = f"{component}: {summary_text}"
    else:
        title = summary_text
    return _truncate(title, max_length=max_length)


def render_pr_summary_block(summary: Any) -> str:
    return _render_list_block("Summary", _to_lines(summary))


def render_pr_validation_block(validation: Any) -> str:
    return _render_list_block("Validation", _to_lines(validation))


def render_pr_scope_notes_block(scope_notes: Any) -> str:
    return _render_list_block("Scope notes", _to_lines(scope_notes))


def _render_pr_what_changed_block(what_changed: Any) -> str:
    return _render_list_block("What changed", _to_lines(what_changed))


def render_pr_body(
    *,
    summary: Any,
    what_changed: Any = None,
    validation: Any = None,
    scope_notes: Any = None,
    policy: Mapping[str, Any] | None = None,
) -> str:
    loaded_policy = dict(policy or _load_policy())
    pr_policy = loaded_policy.get("pr") if isinstance(loaded_policy, Mapping) else {}
    if not isinstance(pr_policy, Mapping):
        pr_policy = {}
    body_policy = pr_policy.get("body")
    if not isinstance(body_policy, Mapping):
        body_policy = {}
    configured_sections = body_policy.get("sections")
    sections = (
        [str(item) for item in configured_sections if _coerce_text(item)]
        if isinstance(configured_sections, Sequence) and not isinstance(configured_sections, (str, bytes))
        else ["Summary", "What changed", "Validation", "Scope notes"]
    )

    block_map: dict[str, str] = {
        "Summary": render_pr_summary_block(summary),
        "What changed": _render_pr_what_changed_block(what_changed),
        "Validation": render_pr_validation_block(validation),
        "Scope notes": render_pr_scope_notes_block(scope_notes),
    }

    ordered_blocks = [block_map[name] for name in sections if name in block_map]
    if not ordered_blocks:
        ordered_blocks = [
            render_pr_summary_block(summary),
            _render_pr_what_changed_block(what_changed),
            render_pr_validation_block(validation),
            render_pr_scope_notes_block(scope_notes),
        ]
    return "\n\n".join(ordered_blocks).strip()


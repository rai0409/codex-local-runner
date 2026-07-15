from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_FIX_CONSTRAINTS = [
    "Do not commit.",
    "Do not tag.",
    "Do not push.",
    "Do not create new files unless they are listed as expected modified files.",
    "Do not modify any file outside the target repository.",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _read_json(path: str | Path) -> tuple[dict[str, Any], str]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}, f"unreadable: {path}"
    except json.JSONDecodeError:
        return {}, f"invalid json: {path}"
    if not isinstance(payload, dict):
        return {}, f"not an object: {path}"
    return payload, ""


def build_fix_prompt_text(
    *,
    digest: Mapping[str, Any],
    effect_spec: Mapping[str, Any],
    original_prompt_text: str = "",
    extra_constraints: list[str] | tuple[str, ...] | None = None,
) -> str:
    repo_path = _normalize_text(effect_spec.get("repo_path"), default="<unknown repo>")
    expected_modified = list(effect_spec.get("expected_modified_files", []) or [])
    expected_unmodified = list(effect_spec.get("expected_unmodified_files", []) or [])
    required_text = effect_spec.get("required_text", {}) or {}
    errors = list(digest.get("effect_verification_errors", []) or [])
    failure_class = _normalize_text(digest.get("failure_class"), default="unknown")
    stop_reason = _normalize_text(digest.get("stop_reason"), default="unknown")

    lines: list[str] = [
        "You are fixing a failed automated change attempt.",
        f"You are operating only inside {repo_path}.",
        "",
        "## Failure evidence",
        f"- failure_class: {failure_class}",
        f"- stop_reason: {stop_reason}",
    ]
    if errors:
        lines.append("- verification errors:")
        lines.extend(f"  - {error}" for error in errors)
    else:
        lines.append("- verification errors: none recorded")

    lines.extend(["", "## Required effects (must all be satisfied after your fix)"])
    if expected_modified:
        lines.append("- Files that must be modified: " + ", ".join(expected_modified))
    if expected_unmodified:
        lines.append("- Files that must NOT be modified: " + ", ".join(expected_unmodified))
    for rel, snippets in required_text.items():
        lines.append(f"- {rel} must contain:")
        lines.extend(f"  - {snippet}" for snippet in snippets)
    forbidden = list(effect_spec.get("forbidden_paths", []) or [])
    if forbidden:
        lines.append("- Paths that must NOT exist: " + ", ".join(forbidden))

    if _normalize_text(original_prompt_text):
        lines.extend(
            [
                "",
                "## Original task prompt (for context)",
                original_prompt_text.strip(),
            ]
        )

    lines.extend(["", "## Constraints"])
    constraints = list(DEFAULT_FIX_CONSTRAINTS)
    for constraint in extra_constraints or []:
        text = _normalize_text(constraint)
        if text and text not in constraints:
            constraints.append(text)
    lines.extend(f"- {constraint}" for constraint in constraints)

    lines.extend(
        [
            "",
            "Apply the smallest change that satisfies all required effects.",
            "After editing, reply only with:",
            '{"status":"success","summary":"targeted fix applied"}',
        ]
    )
    return "\n".join(lines) + "\n"


def write_fix_prompt(
    *,
    digest_path: str | Path,
    effect_spec_path: str | Path,
    out_path: str | Path,
    original_prompt_path: str | Path | None = None,
    extra_constraints: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build a targeted-fix prompt file from a failure digest and effect spec. Offline only."""
    digest, digest_error = _read_json(digest_path)
    effect_spec, spec_error = _read_json(effect_spec_path)
    errors = [e for e in (digest_error, spec_error) if e]
    original_prompt_text = ""
    if original_prompt_path is not None:
        try:
            original_prompt_text = Path(original_prompt_path).read_text(encoding="utf-8")
        except OSError:
            errors.append(f"original prompt unreadable: {original_prompt_path}")
    result: dict[str, Any] = {
        "status": "blocked" if errors else "success",
        "errors": errors,
        "fix_prompt_path": Path(out_path).as_posix(),
        "digest_path": Path(digest_path).as_posix(),
        "effect_spec_path": Path(effect_spec_path).as_posix(),
        "failure_class": _normalize_text(digest.get("failure_class"), default="unknown"),
        "codex_invoked": False,
        "local_only": True,
        "generated_at": _utc_now(),
    }
    if errors:
        return result
    prompt_text = build_fix_prompt_text(
        digest=digest,
        effect_spec=effect_spec,
        original_prompt_text=original_prompt_text,
        extra_constraints=extra_constraints,
    )
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(prompt_text, encoding="utf-8")
    return result


__all__ = [
    "DEFAULT_FIX_CONSTRAINTS",
    "build_fix_prompt_text",
    "write_fix_prompt",
]

"""Canonical prompt-builder implementation for codex-local-runner.

Compatibility note:
- Root-level ``prompt_builder.py`` is a thin wrapper and should remain
  compatibility-only.
- ``build_prompt(task, base_rules_path=...)`` preserves the historical app path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping

from automation.planning.task_classifier import classify_task_type
from automation.planning.template_registry import load_template

_DEFAULT_REPO_PROFILE = "prompts/repo_profiles/codex_local_runner.md"
_CANONICAL_TASK_TYPES = {
    "inspect_read_only",
    "correction_from_current_state",
    "regenerate_after_reset",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read_text(path: str) -> str:
    return (_repo_root() / path).read_text(encoding="utf-8").strip()


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    normalized: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            normalized.append(text)
    return normalized


def _render_bullets(items: list[str], *, empty: str = "(none)") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def _render_commands(items: list[str]) -> str:
    if not items:
        return "```bash\n# (none provided)\n```"
    return "```bash\n" + "\n".join(items) + "\n```"


def _include_canonical_vocabulary(task: Mapping[str, Any], *, task_type: str) -> bool:
    explicit = task.get("include_canonical_vocabulary")
    if isinstance(explicit, bool):
        return explicit
    return task_type in _CANONICAL_TASK_TYPES


def _legacy_render_list(values: Any) -> str:
    cleaned = [str(value).strip() for value in list(values) if str(value).strip()]
    if not cleaned:
        return "- none"
    return "\n".join(f"- {item}" for item in cleaned)


def _build_legacy_prompt(task: Mapping[str, Any], *, base_rules_path: str) -> str:
    base_rules = Path(base_rules_path).read_text(encoding="utf-8").strip()
    goal = str(task.get("goal", "")).strip()
    repo_path = str(task.get("repo_path", "")).strip()
    notes = str(task.get("notes", "")).strip() or "(none)"

    allowed_files = _legacy_render_list(task.get("allowed_files", []))
    forbidden_files = _legacy_render_list(task.get("forbidden_files", []))
    validation_commands = _legacy_render_list(task.get("validation_commands", []))

    return (
        f"{base_rules}\n\n"
        "## Task Input\n"
        f"Repository path:\n{repo_path}\n\n"
        f"Goal:\n{goal}\n\n"
        "Allowed files:\n"
        f"{allowed_files}\n\n"
        "Forbidden files:\n"
        f"{forbidden_files}\n\n"
        "Validation commands:\n"
        f"{validation_commands}\n\n"
        "Notes:\n"
        f"{notes}\n"
    )


def build_prompt(task: Mapping[str, Any], base_rules_path: str | None = None) -> str:
    """Build a prompt from canonical planning assets or legacy base-rules mode."""
    if base_rules_path is not None:
        return _build_legacy_prompt(task, base_rules_path=base_rules_path)

    task_type = classify_task_type(task.get("task_type"))

    repository = str(task.get("repository") or "codex-local-runner").strip()
    mode = str(task.get("mode") or "Implement").strip()
    primary_goal = str(task.get("primary_goal") or "(not provided)").strip()

    read_files = _as_list(task.get("read_files"))
    non_goals = _as_list(task.get("non_goals"))
    repo_constraints = _as_list(task.get("repo_constraints"))
    allowed_files = _as_list(task.get("allowed_files"))
    forbidden_files = _as_list(task.get("forbidden_files"))
    implementation_requirements = _as_list(task.get("implementation_requirements"))
    validation_commands = _as_list(task.get("validation_commands"))
    success_criteria = _as_list(task.get("success_criteria"))
    final_output_requirements = _as_list(task.get("final_output_requirements"))

    repo_profile_path = str(task.get("repo_profile_path") or _DEFAULT_REPO_PROFILE).strip()

    repo_context_block = _read_text("prompts/blocks/repo_context.md")
    hard_constraints_block = _read_text("prompts/blocks/hard_constraints.md")
    canonical_vocabulary_block = _read_text("prompts/blocks/canonical_vocabulary.md")
    validation_block = _read_text("prompts/blocks/validation_block.md")
    output_requirements_block = _read_text("prompts/blocks/output_requirements.md")
    repo_profile_text = _read_text(repo_profile_path)
    template_text = load_template(task_type)

    canonical_section = canonical_vocabulary_block
    if not _include_canonical_vocabulary(task, task_type=task_type):
        canonical_section = "Not required for this task type."

    sections = [
        "## 1. Repository Identity / Read-First Requirement\n"
        f"Repository: {repository}\n"
        "Read these files first (proof required):\n"
        f"{_render_bullets(read_files)}\n\n"
        f"{repo_context_block}\n\n"
        "Repo profile:\n"
        f"{repo_profile_text}",
        "## 2. Mode\n"
        f"{mode}",
        "## 3. Primary Goal\n"
        f"{primary_goal}",
        "## 4. Non-Goals\n"
        f"{_render_bullets(non_goals)}",
        "## 5. Repo-Grounded Constraints\n"
        f"{_render_bullets(repo_constraints)}\n\n"
        f"{hard_constraints_block}",
        "## 6. Canonical Vocabulary / Compatibility Notes\n"
        f"{canonical_section}",
        "## 7. Allowed Files\n"
        f"{_render_bullets(allowed_files)}",
        "## 8. Forbidden Files\n"
        f"{_render_bullets(forbidden_files)}",
        "## 9. Implementation Requirements\n"
        f"Task type: `{task_type}`\n\n"
        f"{_render_bullets(implementation_requirements)}\n\n"
        "Template guidance:\n"
        f"{template_text}",
        "## 10. Validation Commands\n"
        f"{validation_block}\n\n"
        f"{_render_commands(validation_commands)}",
        "## 11. Success Criteria\n"
        f"{_render_bullets(success_criteria)}",
        "## 12. Final Output Requirements\n"
        f"{output_requirements_block}\n\n"
        f"{_render_bullets(final_output_requirements)}",
    ]

    return "\n\n".join(sections).strip() + "\n"

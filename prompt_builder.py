from __future__ import annotations

from pathlib import Path


def _render_list(values: list[str]) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    if not cleaned:
        return "- none"
    return "\n".join(f"- {item}" for item in cleaned)


def build_prompt(task: dict, base_rules_path: str) -> str:
    base_rules = Path(base_rules_path).read_text(encoding="utf-8").strip()

    goal = str(task.get("goal", "")).strip()
    repo_path = str(task.get("repo_path", "")).strip()
    notes = str(task.get("notes", "")).strip() or "(none)"

    allowed_files = _render_list(list(task.get("allowed_files", [])))
    forbidden_files = _render_list(list(task.get("forbidden_files", [])))
    validation_commands = _render_list(list(task.get("validation_commands", [])))

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

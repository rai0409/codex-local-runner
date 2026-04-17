from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Mapping

from automation.planning.project_planner import PR_PLAN_FILENAME
from automation.planning.project_planner import PROJECT_BRIEF_FILENAME
from automation.planning.project_planner import REPO_FACTS_FILENAME
from automation.planning.project_planner import ROADMAP_FILENAME

_SECTION_HEADINGS = (
    "## 1. Objective",
    "## 2. Strict Scope",
    "## 3. Required Outcomes",
    "## 4. Non-goals",
    "## 5. Constraints",
    "## 6. Validation",
    "## 7. Required Final Output",
)


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def _normalize_string_list(value: Any, *, sort_items: bool = False) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for raw in value:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    if sort_items:
        return sorted(items)
    return items


def _render_bullets(items: list[str], *, empty: str = "(none)") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return payload


def load_planning_artifacts(artifacts_dir: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(artifacts_dir)
    return {
        "project_brief": _read_json_object(root / PROJECT_BRIEF_FILENAME),
        "repo_facts": _read_json_object(root / REPO_FACTS_FILENAME),
        "roadmap": _read_json_object(root / ROADMAP_FILENAME),
        "pr_plan": _read_json_object(root / PR_PLAN_FILENAME),
    }


def _build_required_outcomes(pr: Mapping[str, Any]) -> list[str]:
    fields = [
        f"pr_id: {_normalize_text(pr.get('pr_id'))}",
        f"title: {_normalize_text(pr.get('title'))}",
        f"exact_scope: {_normalize_text(pr.get('exact_scope'))}",
        "touched_files: " + ", ".join(_normalize_string_list(pr.get("touched_files"), sort_items=True) or ["(none)"]),
        "forbidden_files: " + ", ".join(_normalize_string_list(pr.get("forbidden_files"), sort_items=True) or ["(none)"]),
        "acceptance_criteria: " + ", ".join(_normalize_string_list(pr.get("acceptance_criteria")) or ["(none)"]),
        "validation_commands: " + ", ".join(_normalize_string_list(pr.get("validation_commands")) or ["(none)"]),
        f"rollback_notes: {_normalize_text(pr.get('rollback_notes'), default='(none)')}",
        f"tier_category: {_normalize_text(pr.get('tier_category'), default='(none)')}",
        "depends_on: " + ", ".join(_normalize_string_list(pr.get("depends_on")) or ["(none)"]),
    ]
    return fields


def _build_non_goals(pr: Mapping[str, Any]) -> list[str]:
    non_goals = [
        "Do not modify files outside the strict scope touched_files list.",
        "Do not broaden to unrelated refactors or additional task boundaries.",
        "Do not add scheduler/retry-controller/rollback execution behavior.",
        "Do not add GitHub write behavior in this task unit.",
    ]
    forbidden_files = _normalize_string_list(pr.get("forbidden_files"), sort_items=True)
    if forbidden_files:
        non_goals.append("Forbidden files: " + ", ".join(forbidden_files))
    return non_goals


def _build_constraints(
    *,
    project_brief: Mapping[str, Any],
    repo_facts: Mapping[str, Any],
    pr_plan: Mapping[str, Any],
    pr: Mapping[str, Any],
) -> list[str]:
    constraints = [
        "Additive changes only.",
        "No broad refactor.",
        "No out-of-scope behavior changes.",
        (
            "Treat repo_facts.default_branch as repository default-branch semantics only: "
            f"{_normalize_text(repo_facts.get('default_branch'), default='(unknown)')}"
        ),
        (
            "Preserve planner tier_category exactly: "
            f"{_normalize_text(pr.get('tier_category'), default='(none)')}"
        ),
    ]

    project_constraints = _normalize_string_list(project_brief.get("constraints"))
    for item in project_constraints:
        constraints.append(item)

    depends_on = _normalize_string_list(pr.get("depends_on"))
    if depends_on:
        constraints.append("Depends on: " + ", ".join(depends_on))

    for optional_key in ("canonical_surface_notes", "compatibility_notes", "planning_warnings"):
        for note in _normalize_string_list(pr_plan.get(optional_key)):
            constraints.append(f"{optional_key}: {note}")

    return constraints


def _build_validation(pr: Mapping[str, Any], repo_facts: Mapping[str, Any]) -> list[str]:
    pr_commands = _normalize_string_list(pr.get("validation_commands"))
    if pr_commands:
        return pr_commands

    # Conservative fallback only when PR slice omitted explicit validation.
    return _normalize_string_list(repo_facts.get("build_commands"))


def _build_required_final_output() -> list[str]:
    return [
        "List of changed files.",
        "Summary of changes made for this PR slice.",
        "Validation command results.",
        "Any unresolved risks or follow-up notes.",
    ]


def _compile_prompt_markdown(
    *,
    project_brief: Mapping[str, Any],
    repo_facts: Mapping[str, Any],
    pr_plan: Mapping[str, Any],
    pr: Mapping[str, Any],
) -> str:
    pr_id = _normalize_text(pr.get("pr_id"), default="(unknown)")
    title = _normalize_text(pr.get("title"), default="(untitled)")
    exact_scope = _normalize_text(pr.get("exact_scope"), default="(none)")

    objective = [
        f"Execute exactly one PR slice: {pr_id}",
        f"Title: {title}",
        f"Objective scope: {exact_scope}",
    ]

    strict_scope = [
        f"pr_id: {pr_id}",
        f"exact_scope: {exact_scope}",
        "Touched files:",
    ]
    touched_files = _normalize_string_list(pr.get("touched_files"), sort_items=True)
    strict_scope.extend([f"- {path}" for path in touched_files] or ["- (none)"])

    sections = [
        (_SECTION_HEADINGS[0], _render_bullets(objective)),
        (_SECTION_HEADINGS[1], "\n".join(strict_scope)),
        (_SECTION_HEADINGS[2], _render_bullets(_build_required_outcomes(pr))),
        (_SECTION_HEADINGS[3], _render_bullets(_build_non_goals(pr))),
        (
            _SECTION_HEADINGS[4],
            _render_bullets(
                _build_constraints(
                    project_brief=project_brief,
                    repo_facts=repo_facts,
                    pr_plan=pr_plan,
                    pr=pr,
                )
            ),
        ),
        (_SECTION_HEADINGS[5], _render_bullets(_build_validation(pr, repo_facts))),
        (_SECTION_HEADINGS[6], _render_bullets(_build_required_final_output())),
    ]

    return "\n\n".join(f"{heading}\n{body}" for heading, body in sections).strip() + "\n"


def compile_prompt_units(artifacts: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    project_brief = artifacts.get("project_brief", {})
    repo_facts = artifacts.get("repo_facts", {})
    pr_plan = artifacts.get("pr_plan", {})

    prs = pr_plan.get("prs") if isinstance(pr_plan.get("prs"), list) else []

    units: list[dict[str, Any]] = []
    for pr_raw in prs:
        if not isinstance(pr_raw, Mapping):
            continue
        pr = dict(pr_raw)
        prompt_markdown = _compile_prompt_markdown(
            project_brief=project_brief,
            repo_facts=repo_facts,
            pr_plan=pr_plan,
            pr=pr,
        )

        unit = {
            "pr_id": _normalize_text(pr.get("pr_id"), default=""),
            "title": _normalize_text(pr.get("title"), default=""),
            "exact_scope": _normalize_text(pr.get("exact_scope"), default=""),
            "touched_files": _normalize_string_list(pr.get("touched_files"), sort_items=True),
            "forbidden_files": _normalize_string_list(pr.get("forbidden_files"), sort_items=True),
            "acceptance_criteria": _normalize_string_list(pr.get("acceptance_criteria")),
            "validation_commands": _normalize_string_list(pr.get("validation_commands")),
            "rollback_notes": _normalize_text(pr.get("rollback_notes"), default=""),
            "tier_category": _normalize_text(pr.get("tier_category"), default=""),
            "depends_on": _normalize_string_list(pr.get("depends_on")),
            "canonical_surface_notes": _normalize_string_list(pr_plan.get("canonical_surface_notes")),
            "compatibility_notes": _normalize_string_list(pr_plan.get("compatibility_notes")),
            "planning_warnings": _normalize_string_list(pr_plan.get("planning_warnings")),
            "codex_task_prompt_md": prompt_markdown,
        }
        units.append(unit)

    return units


def write_compiled_prompt_units(units: list[Mapping[str, Any]], out_dir: str | Path) -> tuple[str, ...]:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for index, unit in enumerate(units, start=1):
        pr_id = _normalize_text(unit.get("pr_id"), default=f"slice-{index:02d}")
        unit_dir = root / pr_id
        unit_dir.mkdir(parents=True, exist_ok=True)
        prompt_path = unit_dir / "codex_task_prompt.md"
        prompt_path.write_text(
            _normalize_text(unit.get("codex_task_prompt_md"), default=""),
            encoding="utf-8",
        )
        written.append(str(prompt_path))

    return tuple(written)

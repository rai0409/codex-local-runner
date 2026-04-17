from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from automation.planning.project_planner import PR_PLAN_FILENAME
from automation.planning.project_planner import PROJECT_BRIEF_FILENAME
from automation.planning.project_planner import REPO_FACTS_FILENAME
from automation.planning.project_planner import ROADMAP_FILENAME
from automation.planning.prompt_compiler import compile_prompt_units
from automation.planning.prompt_compiler import load_planning_artifacts
from automation.planning.prompt_compiler import write_compiled_prompt_units


class PromptCompilerTests(unittest.TestCase):
    def _artifacts(self) -> dict[str, dict[str, object]]:
        return {
            "project_brief": {
                "project_id": "proj-compiler",
                "objective": "Compile PR slices into deterministic prompts",
                "success_definition": "Each PR slice has one prompt",
                "constraints": [
                    "Preserve additive behavior",
                ],
                "non_goals": [
                    "No execution authority changes",
                ],
                "allowed_risk_level": "conservative",
                "target_repo": "codex-local-runner",
                "target_branch": "main",
                "requested_by": "operator",
                "created_at": "2026-04-18T00:00:00+00:00",
            },
            "repo_facts": {
                "repo": "codex-local-runner",
                "default_branch": "main",
                "relevant_paths": ["automation/planning", "tests"],
                "entrypoints": ["scripts/build_planning_artifacts.py"],
                "tests_available": ["tests/test_project_planner.py"],
                "build_commands": ["python3 -m unittest discover -s tests"],
                "lint_commands": [],
                "current_branch_rules": ["require_ci_green=true"],
                "sensitive_paths": ["orchestrator/**"],
                "source_of_truth_commit": "abc123",
            },
            "roadmap": {
                "roadmap_id": "proj-compiler-roadmap-v1",
                "milestones": [],
                "dependency_edges": [],
                "blocked_by": [],
                "estimated_risk": "medium",
            },
            "pr_plan": {
                "plan_id": "proj-compiler-plan-v1",
                "prs": [
                    {
                        "pr_id": "proj-compiler-plan-v1-pr-01",
                        "title": "[planning] Add prompt compiler",
                        "exact_scope": "Add prompt compiler module and tests",
                        "touched_files": [
                            "automation/planning/prompt_compiler.py",
                            "tests/test_prompt_compiler.py",
                        ],
                        "forbidden_files": ["orchestrator/main.py"],
                        "acceptance_criteria": ["Prompt sections are deterministic"],
                        "validation_commands": ["python3 -m unittest tests.test_prompt_compiler -v"],
                        "rollback_notes": "Revert compiler changes if contracts drift.",
                        "tier_category": "runtime_fix_low_risk",
                        "depends_on": [],
                    },
                    {
                        "pr_id": "proj-compiler-plan-v1-pr-02",
                        "title": "[execution] Add adapter normalization",
                        "exact_scope": "Add codex executor adapter module and tests",
                        "touched_files": [
                            "automation/execution/codex_executor_adapter.py",
                            "tests/test_codex_executor_adapter.py",
                        ],
                        "forbidden_files": ["orchestrator/merge_executor.py"],
                        "acceptance_criteria": ["Result normalization is conservative"],
                        "validation_commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"],
                        "rollback_notes": "Revert adapter changes if normalization contract breaks.",
                        "tier_category": "runtime_fix_high_risk",
                        "depends_on": ["proj-compiler-plan-v1-pr-01"],
                    },
                ],
                "canonical_surface_notes": [
                    "inspect_job remains the human-facing authority",
                ],
                "compatibility_notes": [
                    "legacy replan_input.* remains available",
                ],
                "planning_warnings": [
                    "none",
                ],
            },
        }

    def test_compiled_prompt_structure_and_section_ordering(self) -> None:
        units = compile_prompt_units(self._artifacts())
        self.assertEqual(len(units), 2)

        prompt = units[0]["codex_task_prompt_md"]
        headings = [
            "## 1. Objective",
            "## 2. Strict Scope",
            "## 3. Required Outcomes",
            "## 4. Non-goals",
            "## 5. Constraints",
            "## 6. Validation",
            "## 7. Required Final Output",
        ]
        positions = [prompt.index(heading) for heading in headings]
        self.assertEqual(positions, sorted(positions))

    def test_prompt_generation_is_deterministic(self) -> None:
        artifacts = self._artifacts()
        first = compile_prompt_units(artifacts)
        second = compile_prompt_units(artifacts)
        self.assertEqual(first, second)

    def test_pr_slice_fields_are_preserved(self) -> None:
        units = compile_prompt_units(self._artifacts())
        unit = units[1]
        self.assertEqual(unit["pr_id"], "proj-compiler-plan-v1-pr-02")
        self.assertEqual(unit["tier_category"], "runtime_fix_high_risk")
        self.assertEqual(
            unit["touched_files"],
            [
                "automation/execution/codex_executor_adapter.py",
                "tests/test_codex_executor_adapter.py",
            ],
        )
        self.assertEqual(unit["forbidden_files"], ["orchestrator/merge_executor.py"])
        self.assertEqual(
            unit["validation_commands"],
            ["python3 -m unittest tests.test_codex_executor_adapter -v"],
        )

    def test_optional_planner_metadata_is_preserved(self) -> None:
        units = compile_prompt_units(self._artifacts())
        for unit in units:
            self.assertEqual(
                unit["canonical_surface_notes"],
                ["inspect_job remains the human-facing authority"],
            )
            self.assertEqual(
                unit["compatibility_notes"],
                ["legacy replan_input.* remains available"],
            )
            self.assertEqual(unit["planning_warnings"], ["none"])

    def test_load_and_write_compiled_prompt_units(self) -> None:
        artifacts = self._artifacts()
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / PROJECT_BRIEF_FILENAME).write_text(
                json.dumps(artifacts["project_brief"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (root / REPO_FACTS_FILENAME).write_text(
                json.dumps(artifacts["repo_facts"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (root / ROADMAP_FILENAME).write_text(
                json.dumps(artifacts["roadmap"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (root / PR_PLAN_FILENAME).write_text(
                json.dumps(artifacts["pr_plan"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            loaded = load_planning_artifacts(root)
            units = compile_prompt_units(loaded)
            written_paths = write_compiled_prompt_units(units, root / "compiled")

            self.assertEqual(len(written_paths), 2)
            for path_value in written_paths:
                path = Path(path_value)
                self.assertTrue(path.exists())
                self.assertEqual(path.name, "codex_task_prompt.md")


if __name__ == "__main__":
    unittest.main()

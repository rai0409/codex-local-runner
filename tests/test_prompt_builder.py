from __future__ import annotations

import unittest

from automation.planning.prompt_builder import build_prompt
from automation.planning.template_registry import get_template_name


class PromptBuilderTests(unittest.TestCase):
    def _base_task(self) -> dict[str, object]:
        return {
            "task_type": "inspect_read_only",
            "repository": "codex-local-runner",
            "mode": "Implement",
            "primary_goal": "Create a narrow prompt for inspect-only update.",
            "read_files": ["README.md", "AGENTS.md"],
            "non_goals": ["no execution runtime"],
            "repo_constraints": ["accepted-vs-execution separation remains intact"],
            "allowed_files": ["scripts/inspect_job.py", "tests/test_inspect_job.py"],
            "forbidden_files": ["run_codex.py"],
            "implementation_requirements": ["keep diff minimal"],
            "validation_commands": ["pytest -q tests/test_inspect_job.py"],
            "success_criteria": ["deterministic output"],
            "final_output_requirements": ["files inspected and why"],
        }

    def test_same_input_produces_same_prompt(self) -> None:
        task = self._base_task()
        prompt_a = build_prompt(task)
        prompt_b = build_prompt(task)
        self.assertEqual(prompt_a, prompt_b)

    def test_template_selected_for_known_task_types(self) -> None:
        self.assertEqual(get_template_name("inspect_read_only"), "inspect_read_only.md")
        self.assertEqual(get_template_name("docs_only"), "docs_only.md")
        self.assertEqual(get_template_name("test_only"), "test_only.md")
        self.assertEqual(
            get_template_name("correction_from_current_state"),
            "correction_from_current_state.md",
        )
        self.assertEqual(
            get_template_name("regenerate_after_reset"),
            "regenerate_after_reset.md",
        )

    def test_unknown_task_type_falls_back_to_docs_only_template(self) -> None:
        task = self._base_task()
        task["task_type"] = "unknown_type"
        prompt = build_prompt(task)
        self.assertIn("Task type: `docs_only`", prompt)
        self.assertIn("Template: docs_only", prompt)

    def test_required_sections_are_present_in_order(self) -> None:
        prompt = build_prompt(self._base_task())
        headings = [
            "## 1. Repository Identity / Read-First Requirement",
            "## 2. Mode",
            "## 3. Primary Goal",
            "## 4. Non-Goals",
            "## 5. Repo-Grounded Constraints",
            "## 6. Canonical Vocabulary / Compatibility Notes",
            "## 7. Allowed Files",
            "## 8. Forbidden Files",
            "## 9. Implementation Requirements",
            "## 10. Validation Commands",
            "## 11. Success Criteria",
            "## 12. Final Output Requirements",
        ]
        indices = [prompt.index(heading) for heading in headings]
        self.assertEqual(indices, sorted(indices))

    def test_prompt_prefers_canonical_vocabulary_over_compatibility_aliases(self) -> None:
        prompt = build_prompt(self._base_task())
        self.assertLess(prompt.index("`recovery_decision`"), prompt.index("`recommended_action`"))
        self.assertLess(prompt.index("`failure_codes`"), prompt.index("`policy_reasons`"))

    def test_prompt_keeps_execution_authorization_out_of_scope(self) -> None:
        prompt = build_prompt(self._base_task())
        self.assertIn("Do not imply execution authorization", prompt)
        self.assertIn("visibility-focused", prompt)


if __name__ == "__main__":
    unittest.main()

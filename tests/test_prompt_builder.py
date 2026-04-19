from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from automation.planning.prompt_builder import build_prompt as build_prompt_canonical
from automation.planning.task_classifier import classify_task_type
from automation.planning.template_registry import get_template_name
from prompt_builder import build_prompt as build_prompt_compat


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
        prompt_a = build_prompt_canonical(task)
        prompt_b = build_prompt_canonical(task)
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
        prompt = build_prompt_canonical(task)
        self.assertIn("Task type: `docs_only`", prompt)
        self.assertIn("Template: docs_only", prompt)

    def test_required_sections_are_present_in_order(self) -> None:
        prompt = build_prompt_canonical(self._base_task())
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
        prompt = build_prompt_canonical(self._base_task())
        self.assertLess(prompt.index("`recovery_decision`"), prompt.index("`recommended_action`"))
        self.assertLess(prompt.index("`failure_codes`"), prompt.index("`policy_reasons`"))

    def test_prompt_keeps_execution_authorization_out_of_scope(self) -> None:
        prompt = build_prompt_canonical(self._base_task())
        self.assertIn("Do not imply execution authorization", prompt)
        self.assertIn("visibility-focused", prompt)

    def test_compat_entrypoint_matches_canonical_for_modern_task(self) -> None:
        task = self._base_task()
        self.assertEqual(build_prompt_canonical(task), build_prompt_compat(task))

    def test_legacy_base_rules_mode_is_preserved_and_identical_across_paths(self) -> None:
        legacy_task = {
            "repo_path": "/tmp/repo",
            "goal": "legacy prompt shape",
            "allowed_files": ["a.py", "b.py"],
            "forbidden_files": [],
            "validation_commands": ["pytest -q"],
            "notes": "",
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_rules_path = Path(tmp_dir) / "base_rules.txt"
            base_rules_path.write_text("Base rules line.", encoding="utf-8")
            expected = (
                "Base rules line.\n\n"
                "## Task Input\n"
                "Repository path:\n"
                "/tmp/repo\n\n"
                "Goal:\n"
                "legacy prompt shape\n\n"
                "Allowed files:\n"
                "- a.py\n"
                "- b.py\n\n"
                "Forbidden files:\n"
                "- none\n\n"
                "Validation commands:\n"
                "- pytest -q\n\n"
                "Notes:\n"
                "(none)\n"
            )
            canonical_prompt = build_prompt_canonical(legacy_task, str(base_rules_path))
            compat_prompt = build_prompt_compat(legacy_task, str(base_rules_path))
        self.assertEqual(canonical_prompt, expected)
        self.assertEqual(compat_prompt, expected)
        self.assertEqual(canonical_prompt, compat_prompt)

    def test_task_classification_semantics_unchanged(self) -> None:
        self.assertEqual(classify_task_type("inspect_read_only"), "inspect_read_only")
        self.assertEqual(classify_task_type("inspect_read_only_extension"), "inspect_read_only")
        self.assertEqual(classify_task_type("unknown"), "docs_only")


if __name__ == "__main__":
    unittest.main()

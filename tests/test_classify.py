from __future__ import annotations

import unittest

from orchestrator.classify import classify_changes


class ClassifyTests(unittest.TestCase):
    def test_docs_only_classification(self) -> None:
        result = classify_changes(
            declared_category="docs_only",
            changed_files=["docs/reviewer_handoff.md", "docs/reviewer_runbook.md"],
        )

        self.assertEqual(result.observed_category, "docs_only")
        self.assertTrue(result.declared_matches_observed)

    def test_test_only_classification(self) -> None:
        result = classify_changes(
            declared_category="test_only",
            changed_files=["tests/test_merge_gate.py", "tests/test_evaluate.py"],
        )

        self.assertEqual(result.observed_category, "test_only")
        self.assertTrue(result.declared_matches_observed)

    def test_docs_and_tests_classify_as_contract_guard_only(self) -> None:
        result = classify_changes(
            declared_category="contract_guard_only",
            changed_files=["docs/reviewer_handoff.md", "tests/test_execution_path.py"],
        )

        self.assertEqual(result.observed_category, "contract_guard_only")
        self.assertTrue(result.declared_matches_observed)

    def test_touching_adapters_is_runtime_fix_high_risk(self) -> None:
        result = classify_changes(
            declared_category="runtime_fix_high_risk",
            changed_files=["adapters/codex_cli.py"],
        )

        self.assertEqual(result.observed_category, "runtime_fix_high_risk")
        self.assertIn("runtime_sensitive_paths_touched", result.reasons)

    def test_touching_run_codex_is_runtime_fix_high_risk(self) -> None:
        result = classify_changes(
            declared_category="runtime_fix_high_risk",
            changed_files=["run_codex.py"],
        )

        self.assertEqual(result.observed_category, "runtime_fix_high_risk")
        self.assertIn("runtime_sensitive_paths_touched", result.reasons)


if __name__ == "__main__":
    unittest.main()

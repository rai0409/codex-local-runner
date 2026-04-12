from __future__ import annotations

import unittest

from orchestrator.evaluate import evaluate_rubric


class EvaluateTests(unittest.TestCase):
    def test_rubric_fails_when_forbidden_files_are_touched(self) -> None:
        result = evaluate_rubric(
            declared_category="docs_only",
            observed_category="docs_only",
            changed_files=["docs/reviewer_handoff.md", "orchestrator/main.py"],
            additions=10,
            deletions=2,
            required_tests_declared=True,
            required_tests_executed=True,
            required_tests_passed=True,
            ci_green=True,
            rollback_metadata_recorded=True,
        )

        self.assertFalse(result.forbidden_files_untouched)
        self.assertFalse(result.merge_eligible)
        self.assertIn("observed_category_forbidden_paths_touched", result.fail_reasons)

    def test_rubric_fails_when_declared_not_equal_observed(self) -> None:
        result = evaluate_rubric(
            declared_category="docs_only",
            observed_category="test_only",
            changed_files=["tests/test_execution_path.py"],
            additions=5,
            deletions=1,
            required_tests_declared=True,
            required_tests_executed=True,
            required_tests_passed=True,
            ci_green=True,
            rollback_metadata_recorded=True,
        )

        self.assertFalse(result.merge_eligible)
        self.assertIn("declared_category_does_not_match_observed_category", result.fail_reasons)

    def test_rubric_fails_when_required_tests_not_passed(self) -> None:
        result = evaluate_rubric(
            declared_category="test_only",
            observed_category="test_only",
            changed_files=["tests/test_verify_runner.py"],
            additions=7,
            deletions=3,
            required_tests_declared=True,
            required_tests_executed=True,
            required_tests_passed=False,
            ci_green=True,
            rollback_metadata_recorded=True,
        )

        self.assertFalse(result.merge_eligible)
        self.assertIn("required_tests_not_passed", result.fail_reasons)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

from orchestrator.merge_gate import apply_merge_gate
from orchestrator.policy_loader import load_merge_gate_policy
from orchestrator.schemas import RubricEvaluationResult


class MergeGateTests(unittest.TestCase):
    def _rubric(
        self,
        observed_category: str,
        *,
        declared_category: str | None = None,
        forbidden_files_untouched: bool = True,
        diff_size_within_limit: bool = True,
        required_tests_declared: bool = True,
        required_tests_executed: bool = True,
        required_tests_passed: bool = True,
        ci_required_checks_green: bool = True,
    ) -> RubricEvaluationResult:
        return RubricEvaluationResult(
            declared_category=declared_category or observed_category,
            observed_category=observed_category,
            allowed_files_only=True,
            forbidden_files_untouched=forbidden_files_untouched,
            diff_size_within_limit=diff_size_within_limit,
            required_tests_declared=required_tests_declared,
            required_tests_executed=required_tests_executed,
            required_tests_passed=required_tests_passed,
            runtime_semantics_changed=False,
            contract_shape_changed=False,
            reviewer_fields_changed=False,
            ci_required_checks_green=ci_required_checks_green,
            rollback_metadata_recorded=True,
            merge_eligible=(
                forbidden_files_untouched
                and diff_size_within_limit
                and required_tests_declared
                and required_tests_executed
                and required_tests_passed
                and ci_required_checks_green
                and ((declared_category or observed_category) == observed_category)
            ),
            fail_reasons=(),
            warnings=(),
        )

    def test_merge_gate_passes_for_safe_auto_merge_category(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_handoff.md",),
            additions=10,
            deletions=2,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.auto_merge_allowed)
        self.assertEqual(result.fail_reasons, ())
        self.assertTrue(result.policy_eligible)
        self.assertTrue(result.auto_pr_candidate)
        self.assertEqual(result.progression_state, "auto_pr_candidate")
        self.assertEqual(result.progression_fail_reasons, ())

    def test_merge_gate_auto_merge_categories_are_loaded_from_yaml(self) -> None:
        policy = load_merge_gate_policy()
        self.assertEqual(
            set(policy["auto_merge_categories"]),
            {"docs_only", "ci_only", "test_only", "contract_guard_only"},
        )

    def test_merge_gate_rejects_high_risk_category_even_if_other_checks_pass(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("runtime_fix_high_risk"),
            changed_files=("adapters/codex_cli.py",),
            additions=8,
            deletions=1,
        )

        self.assertFalse(result.passed)
        self.assertFalse(result.auto_merge_allowed)
        self.assertIn("category_not_auto_merge_allowed", result.fail_reasons)
        self.assertFalse(result.policy_eligible)
        self.assertFalse(result.auto_pr_candidate)
        self.assertEqual(result.progression_state, "manual_only")

    def test_policy_eligible_for_narrow_safe_category_when_signals_pass(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("test_only"),
            changed_files=("tests/test_merge_gate.py",),
            additions=20,
            deletions=5,
        )

        self.assertTrue(result.policy_eligible)
        self.assertFalse(result.auto_pr_candidate)
        self.assertEqual(result.progression_state, "policy_eligible")

    def test_policy_manual_only_when_declared_observed_mismatch(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric(
                observed_category="docs_only",
                declared_category="test_only",
            ),
            changed_files=("docs/reviewer_handoff.md",),
            additions=10,
            deletions=1,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn(
            "declared_category_does_not_match_observed_category",
            result.progression_fail_reasons,
        )

    def test_policy_manual_only_when_forbidden_path_touched(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric(
                observed_category="docs_only",
                forbidden_files_untouched=False,
            ),
            changed_files=("docs/reviewer_handoff.md", "orchestrator/main.py"),
            additions=12,
            deletions=2,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn("observed_category_forbidden_paths_touched", result.progression_fail_reasons)

    def test_policy_manual_only_when_diff_or_file_count_limit_exceeded(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric(observed_category="docs_only"),
            changed_files=tuple(f"docs/file_{index}.md" for index in range(9)),
            additions=100,
            deletions=30,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn("changed_files_count_exceeded", result.progression_fail_reasons)
        self.assertIn("total_diff_lines_exceeded", result.progression_fail_reasons)

    def test_policy_manual_only_for_unknown_category(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric(observed_category="feature"),
            changed_files=("README.md",),
            additions=3,
            deletions=1,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn("category_not_policy_eligible", result.progression_fail_reasons)

    def test_policy_result_is_deterministic_for_same_inputs(self) -> None:
        rubric = self._rubric("docs_only")
        kwargs = {
            "rubric": rubric,
            "changed_files": ("docs/reviewer_handoff.md",),
            "additions": 4,
            "deletions": 1,
        }
        first = apply_merge_gate(**kwargs)
        second = apply_merge_gate(**kwargs)

        self.assertEqual(first, second)

    def test_auto_pr_candidate_never_broader_than_policy_eligible(self) -> None:
        for category in ("docs_only", "test_only", "feature", "runtime_fix_high_risk"):
            with self.subTest(category=category):
                result = apply_merge_gate(
                    rubric=self._rubric(category),
                    changed_files=("docs/reviewer_handoff.md",),
                    additions=5,
                    deletions=1,
                )
                if result.auto_pr_candidate:
                    self.assertTrue(result.policy_eligible)

    def test_default_without_sufficient_evidence_stays_manual_only(self) -> None:
        result = apply_merge_gate(rubric=self._rubric("docs_only"))

        self.assertFalse(result.policy_eligible)
        self.assertFalse(result.auto_pr_candidate)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn("changed_files_missing", result.progression_fail_reasons)

    def test_generated_or_binary_paths_remain_manual_only(self) -> None:
        generated_result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("build/generated_doc.md",),
            additions=1,
            deletions=0,
        )
        binary_result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/diagram.png",),
            additions=1,
            deletions=0,
        )

        self.assertEqual(generated_result.progression_state, "manual_only")
        self.assertIn("generated_path_touched", generated_result.progression_fail_reasons)
        self.assertEqual(binary_result.progression_state, "manual_only")
        self.assertIn("binary_file_touched", binary_result.progression_fail_reasons)


if __name__ == "__main__":
    unittest.main()

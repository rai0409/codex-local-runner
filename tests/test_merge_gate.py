from __future__ import annotations

import unittest

from orchestrator.merge_gate import apply_merge_gate
from orchestrator.policy_loader import load_merge_gate_policy
from orchestrator.schemas import RubricEvaluationResult


class MergeGateTests(unittest.TestCase):
    def _rubric(self, observed_category: str) -> RubricEvaluationResult:
        return RubricEvaluationResult(
            declared_category=observed_category,
            observed_category=observed_category,
            allowed_files_only=True,
            forbidden_files_untouched=True,
            diff_size_within_limit=True,
            required_tests_declared=True,
            required_tests_executed=True,
            required_tests_passed=True,
            runtime_semantics_changed=False,
            contract_shape_changed=False,
            reviewer_fields_changed=False,
            ci_required_checks_green=True,
            rollback_metadata_recorded=True,
            merge_eligible=True,
            fail_reasons=(),
            warnings=(),
        )

    def test_merge_gate_passes_for_safe_auto_merge_category(self) -> None:
        result = apply_merge_gate(rubric=self._rubric("docs_only"))

        self.assertTrue(result.passed)
        self.assertTrue(result.auto_merge_allowed)
        self.assertEqual(result.fail_reasons, ())

    def test_merge_gate_auto_merge_categories_are_loaded_from_yaml(self) -> None:
        policy = load_merge_gate_policy()
        self.assertEqual(
            set(policy["auto_merge_categories"]),
            {"docs_only", "ci_only", "test_only", "contract_guard_only"},
        )

    def test_merge_gate_rejects_high_risk_category_even_if_other_checks_pass(self) -> None:
        result = apply_merge_gate(rubric=self._rubric("runtime_fix_high_risk"))

        self.assertFalse(result.passed)
        self.assertFalse(result.auto_merge_allowed)
        self.assertIn("category_not_auto_merge_allowed", result.fail_reasons)


if __name__ == "__main__":
    unittest.main()

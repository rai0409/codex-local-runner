from __future__ import annotations

import unittest

from orchestrator.policy_loader import get_change_category_names
from orchestrator.policy_loader import get_change_category_policy
from orchestrator.policy_loader import load_change_categories_policy
from orchestrator.policy_loader import load_merge_gate_policy


class PolicyLoaderTests(unittest.TestCase):
    def test_load_change_categories_policy_contains_expected_categories(self) -> None:
        policy = load_change_categories_policy()
        names = set(policy["categories"].keys())
        self.assertEqual(
            names,
            {
                "docs_only",
                "ci_only",
                "test_only",
                "contract_guard_only",
                "runtime_fix_low_risk",
                "runtime_fix_high_risk",
                "contract_extension",
                "feature",
            },
        )

    def test_get_change_category_names_uses_yaml_policy(self) -> None:
        names = set(get_change_category_names())
        self.assertIn("docs_only", names)
        self.assertIn("feature", names)

    def test_get_change_category_policy_exposes_allowed_and_forbidden_paths(self) -> None:
        docs_only = get_change_category_policy("docs_only")
        assert docs_only is not None
        self.assertEqual(docs_only["allowed_paths"], ("docs/**",))
        self.assertIn("run_codex.py", docs_only["forbidden_paths"])

    def test_load_merge_gate_policy_contains_expected_auto_merge_categories(self) -> None:
        policy = load_merge_gate_policy()
        self.assertEqual(
            set(policy["auto_merge_categories"]),
            {"docs_only", "ci_only", "test_only", "contract_guard_only"},
        )
        self.assertEqual(
            set(policy["auto_progression"]["policy_eligible_categories"]),
            {"docs_only", "test_only"},
        )
        self.assertEqual(
            set(policy["auto_progression"]["auto_pr_candidate_categories"]),
            {"docs_only"},
        )
        self.assertEqual(policy["auto_progression"]["max_changed_files"], 8)
        self.assertEqual(policy["auto_progression"]["max_total_diff_lines"], 120)


if __name__ == "__main__":
    unittest.main()

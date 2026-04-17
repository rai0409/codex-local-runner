from __future__ import annotations

import copy
import unittest

from orchestrator.github_backend import ArtifactGitHubStateBackend
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

    def _github_signals(self, github_state: dict[str, object]) -> dict[str, object]:
        backend = ArtifactGitHubStateBackend()
        return backend.collect(
            request_payload={"repo": "codex-local-runner"},
            result_payload={"github_state": github_state},
        )

    def _policy_with_write_authority(self, **overrides: object) -> dict[str, object]:
        policy = copy.deepcopy(load_merge_gate_policy())
        write_authority = dict(policy.get("write_authority", {}))
        write_authority.update(overrides)
        policy["write_authority"] = write_authority
        return policy

    def _policy_with_retry_replan(self, **overrides: object) -> dict[str, object]:
        policy = copy.deepcopy(load_merge_gate_policy())
        retry_replan = dict(policy.get("retry_replan", {}))
        retry_replan.update(overrides)
        policy["retry_replan"] = retry_replan
        return policy

    def test_merge_gate_passes_for_safe_auto_merge_category(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=10,
            deletions=2,
        )

        self.assertTrue(result.passed)
        self.assertTrue(result.auto_merge_allowed)
        self.assertEqual(result.fail_reasons, ())
        self.assertTrue(result.policy_eligible)
        self.assertTrue(result.auto_pr_candidate)
        self.assertEqual(result.progression_state, "auto_pr_candidate")
        self.assertEqual(result.lifecycle_state, "auto_pr_candidate")
        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "disabled")
        self.assertFalse(result.write_authority["write_actions_allowed"])
        self.assertEqual(result.progression_fail_reasons, ())
        assert result.github_progression is not None
        self.assertEqual(result.github_progression["mode"], "read_only")
        self.assertFalse(result.github_progression["write_actions_allowed"])
        self.assertEqual(result.github_progression["progression"]["state"], "unavailable")
        self.assertFalse(result.github_progression["policy_link"]["auto_pr_candidate_ready"])

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
        self.assertEqual(result.lifecycle_state, "manual_only")

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
        self.assertEqual(result.lifecycle_state, "policy_eligible")

    def test_policy_manual_only_when_declared_observed_mismatch(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric(
                observed_category="docs_only",
                declared_category="test_only",
            ),
            changed_files=("docs/reviewer_runbook.md",),
            additions=10,
            deletions=1,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertEqual(result.lifecycle_state, "manual_only")
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
            "changed_files": ("docs/reviewer_runbook.md",),
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
                    changed_files=("docs/reviewer_runbook.md",),
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

    def test_policy_manual_only_when_ci_signal_not_green(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only", ci_required_checks_green=False),
            changed_files=("docs/reviewer_runbook.md",),
            additions=5,
            deletions=1,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn("required_ci_checks_not_green", result.progression_fail_reasons)

    def test_policy_manual_only_when_diff_line_stats_missing(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=0,
            deletions=0,
            diff_line_stats_present=False,
        )

        self.assertFalse(result.policy_eligible)
        self.assertEqual(result.progression_state, "manual_only")
        self.assertIn("diff_line_stats_missing", result.progression_fail_reasons)

    def test_runtime_or_contract_sensitive_paths_remain_manual_only(self) -> None:
        runtime_sensitive = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("adapters/codex_cli.py",),
            additions=1,
            deletions=0,
        )
        contract_sensitive = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_handoff.md",),
            additions=1,
            deletions=0,
        )

        self.assertEqual(runtime_sensitive.progression_state, "manual_only")
        self.assertIn("runtime_sensitive_paths_touched", runtime_sensitive.progression_fail_reasons)
        self.assertEqual(contract_sensitive.progression_state, "manual_only")
        self.assertIn(
            "contract_shape_related_paths_touched",
            contract_sensitive.progression_fail_reasons,
        )

    def test_progression_fail_reasons_are_stable_machine_usable_values(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric(
                observed_category="docs_only",
                declared_category="test_only",
                forbidden_files_untouched=False,
                diff_size_within_limit=False,
                required_tests_declared=False,
                required_tests_executed=False,
                required_tests_passed=False,
                ci_required_checks_green=False,
            ),
            changed_files=("build/generated_doc.md", "docs/diagram.png"),
            additions=200,
            deletions=0,
            diff_line_stats_present=False,
        )

        self.assertEqual(
            result.progression_fail_reasons,
            (
                "declared_category_does_not_match_observed_category",
                "observed_category_forbidden_paths_touched",
                "diff_size_limit_exceeded",
                "required_tests_not_declared",
                "required_tests_not_executed",
                "required_tests_not_passed",
                "required_ci_checks_not_green",
                "diff_line_stats_missing",
                "total_diff_lines_exceeded",
                "generated_path_touched",
                "binary_file_touched",
            ),
        )

    def test_auto_pr_candidate_can_be_marked_ready_only_with_github_signals(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks": ["unit"],
                "passing_checks": ["unit"],
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )

        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        assert result.github_progression is not None
        self.assertEqual(result.progression_state, "auto_pr_candidate")
        self.assertEqual(result.lifecycle_state, "approved_for_merge")
        self.assertEqual(result.github_progression["progression"]["state"], "ready")
        self.assertTrue(
            result.github_progression["policy_link"]["ready_for_future_auto_pr_progression"]
        )
        self.assertTrue(result.github_progression["policy_link"]["auto_pr_candidate_ready"])

    def test_lifecycle_state_stays_auto_pr_candidate_without_github_readiness(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
        )

        self.assertEqual(result.progression_state, "auto_pr_candidate")
        self.assertEqual(result.lifecycle_state, "auto_pr_candidate")

    def test_lifecycle_state_stays_auto_pr_candidate_when_target_identity_missing(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "auto_pr_candidate")

    def test_lifecycle_state_uses_pending_checks_conservatively(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "pending",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "checks_pending")

    def test_lifecycle_state_does_not_promote_when_checks_state_missing(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "pr_preparable")

    def test_lifecycle_state_requires_sufficient_review_signal(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "pending",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "review_pending")

    def test_lifecycle_state_does_not_promote_when_review_signal_missing(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "review_pending")

    def test_lifecycle_state_does_not_promote_when_mergeability_unknown(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "checks_green")

    def test_lifecycle_state_stays_blocked_on_explicit_merge_block(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "blocked",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "merge_blocked")

    def test_write_authority_disabled_blocks_write_path(self) -> None:
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "disabled")
        self.assertIn(
            "write_authority_disabled",
            result.write_authority["conservative_reasons"],
        )
        self.assertFalse(result.write_authority["write_actions_allowed"])

    def test_write_authority_category_allowlist_blocks_unsafe_category(self) -> None:
        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=False,
            kill_switch=False,
            allowed_categories=("docs_only",),
        )
        result = apply_merge_gate(
            rubric=self._rubric("runtime_fix_high_risk"),
            policy=policy,
            changed_files=("adapters/codex_cli.py",),
            additions=2,
            deletions=1,
        )

        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "blocked")
        self.assertIn(
            "write_category_not_allowed",
            result.write_authority["conservative_reasons"],
        )
        self.assertFalse(result.write_authority["write_actions_allowed"])

    def test_lifecycle_state_alone_does_not_grant_write_permission(self) -> None:
        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=False,
            kill_switch=False,
            allowed_categories=("test_only",),
            required_lifecycle_states=("policy_eligible",),
        )
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("test_only"),
            policy=policy,
            changed_files=("tests/test_merge_gate.py",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        self.assertEqual(result.lifecycle_state, "policy_eligible")
        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "write_preparable")
        self.assertIn(
            "write_auto_pr_candidate_required",
            result.write_authority["conservative_reasons"],
        )
        self.assertFalse(result.write_authority["write_actions_allowed"])

    def test_write_authority_dry_run_blocks_irreversible_behavior(self) -> None:
        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=True,
            kill_switch=False,
            allowed_categories=("docs_only",),
            required_lifecycle_states=("approved_for_merge",),
        )
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            policy=policy,
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "dry_run_only")
        self.assertFalse(result.write_authority["write_actions_allowed"])
        self.assertEqual(result.write_authority["conservative_reasons"], ())

    def test_write_authority_kill_switch_blocks_write_path(self) -> None:
        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=False,
            kill_switch=True,
            allowed_categories=("docs_only",),
        )
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            policy=policy,
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "blocked")
        self.assertIn(
            "write_kill_switch_enabled",
            result.write_authority["conservative_reasons"],
        )
        self.assertFalse(result.write_authority["write_actions_allowed"])

    def test_write_authority_missing_github_readiness_blocks(self) -> None:
        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=False,
            kill_switch=False,
            allowed_categories=("docs_only",),
            required_lifecycle_states=("approved_for_merge",),
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            policy=policy,
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
        )

        assert result.write_authority is not None
        self.assertEqual(result.write_authority["state"], "write_preparable")
        self.assertIn(
            "write_github_state_unavailable",
            result.write_authority["conservative_reasons"],
        )
        self.assertFalse(result.write_authority["write_actions_allowed"])

    def test_write_authority_can_reach_write_allowed_when_all_guards_pass(self) -> None:
        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=False,
            kill_switch=False,
            allowed_categories=("docs_only",),
            required_lifecycle_states=("approved_for_merge",),
        )
        github_signals = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            policy=policy,
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=github_signals,
        )

        assert result.write_authority is not None
        self.assertEqual(result.lifecycle_state, "approved_for_merge")
        self.assertEqual(result.write_authority["state"], "write_allowed")
        self.assertTrue(result.write_authority["write_actions_allowed"])
        self.assertEqual(result.write_authority["conservative_reasons"], ())
        assert result.github_progression is not None
        self.assertEqual(result.github_progression["mode"], "read_only")
        self.assertFalse(result.github_progression["write_actions_allowed"])

    def test_replan_input_classifies_missing_signal_as_retriable(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=4,
            deletions=1,
            diff_line_stats_present=False,
            prior_attempt_count=1,
        )

        assert result.replan_input is not None
        self.assertEqual(result.replan_input["failure_type"], "missing_signal")
        self.assertEqual(result.replan_input["retry_budget_total"], 2)
        self.assertEqual(result.replan_input["retry_budget_remaining"], 1)
        self.assertEqual(result.replan_input["retry_recommendation"], "retry")
        self.assertFalse(result.replan_input["budget_exhausted"])
        self.assertFalse(result.replan_input["escalation_required"])

    def test_replan_input_budget_exhaustion_escalates(self) -> None:
        policy = self._policy_with_retry_replan(max_attempts=2)
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            policy=policy,
            changed_files=("docs/reviewer_runbook.md",),
            additions=4,
            deletions=1,
            diff_line_stats_present=False,
            prior_attempt_count=2,
        )

        assert result.replan_input is not None
        self.assertEqual(result.replan_input["failure_type"], "missing_signal")
        self.assertEqual(result.replan_input["retry_budget_remaining"], 0)
        self.assertTrue(result.replan_input["budget_exhausted"])
        self.assertEqual(result.replan_input["retry_recommendation"], "escalate")
        self.assertTrue(result.replan_input["escalation_required"])

    def test_replan_input_non_retriable_policy_failure_does_not_retry(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only", forbidden_files_untouched=False),
            changed_files=("docs/reviewer_handoff.md", "orchestrator/main.py"),
            additions=10,
            deletions=1,
            prior_attempt_count=0,
        )

        assert result.replan_input is not None
        self.assertEqual(result.replan_input["failure_type"], "policy_failure")
        self.assertFalse(result.replan_input["retriable_failure_type"])
        self.assertEqual(result.replan_input["retry_recommendation"], "escalate")
        self.assertTrue(result.replan_input["escalation_required"])

    def test_replan_input_lifecycle_and_write_authority_blocking_are_distinct(self) -> None:
        pending_checks = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "pending",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        lifecycle_blocked = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=pending_checks,
        )
        assert lifecycle_blocked.replan_input is not None
        self.assertEqual(lifecycle_blocked.replan_input["failure_type"], "lifecycle_blocked")

        policy = self._policy_with_write_authority(
            enabled=True,
            dry_run=False,
            kill_switch=True,
            allowed_categories=("docs_only",),
            required_lifecycle_states=("approved_for_merge",),
        )
        clean_ready = self._github_signals(
            {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks_state": "passing",
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        write_blocked = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            policy=policy,
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            github_signals=clean_ready,
        )
        assert write_blocked.replan_input is not None
        self.assertEqual(
            write_blocked.replan_input["failure_type"],
            "write_authority_blocked",
        )
        self.assertEqual(write_blocked.replan_input["retry_recommendation"], "escalate")

    def test_replan_input_execution_failure_is_retriable_when_budget_available(self) -> None:
        result = apply_merge_gate(
            rubric=self._rubric("docs_only"),
            changed_files=("docs/reviewer_runbook.md",),
            additions=2,
            deletions=1,
            execution_status="failed",
            prior_attempt_count=1,
        )

        assert result.replan_input is not None
        self.assertEqual(result.replan_input["failure_type"], "execution_failure")
        self.assertEqual(result.replan_input["retry_recommendation"], "retry")
        self.assertTrue(result.replan_input["retry_recommended"])


if __name__ == "__main__":
    unittest.main()

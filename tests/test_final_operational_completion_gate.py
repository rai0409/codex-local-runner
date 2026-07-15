from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.final_operational_completion_gate import (
    REQUIRED_NEXT_ACTION,
    RUNTIME_BOUNDARY_REASON,
    build_final_criteria_matrix,
    run_final_operational_completion_gate,
    validate_completion_text,
    verify_final_gate_baselines,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class FinalOperationalCompletionGateTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        required = [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt668_report.json",
            "artifacts/autonomous_runtime/prompt669_report.json",
            "artifacts/autonomous_runtime/prompt670_report.json",
            "artifacts/autonomous_runtime/prompt671_report.json",
            "artifacts/autonomous_runtime/prompt672_report.json",
            "artifacts/autonomous_runtime/prompt673_report.json",
            "artifacts/autonomous_runtime/prompt674_report.json",
            "artifacts/autonomous_runtime/prompt676_report.json",
            "artifacts/autonomous_runtime/prompt677_report.json",
            "artifacts/autonomous_runtime/prompt678_report.json",
            "artifacts/autonomous_runtime/prompt679_report.json",
            "artifacts/autonomous_runtime/prompt680_report.json",
            "artifacts/autonomous_runtime/prompt681_report.json",
            "artifacts/autonomous_runtime/prompt681_operational_readiness_matrix.json",
            "artifacts/autonomous_runtime/prompt682_report.json",
            "artifacts/autonomous_runtime/prompt683_report.json",
            "artifacts/autonomous_runtime/prompt684_report.json",
            "artifacts/autonomous_runtime/prompt685_report.json",
            "artifacts/autonomous_runtime/prompt686_report.json",
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
        )
        for tag in [
            "prompt667-end-to-end-unattended-project-run-acceptance",
            "prompt671-extended-operational-soak-50-ticks",
            "prompt677-increase-multi-prompt-queue-length",
            "prompt679-wire-no-confirmation-profile-into-multi-prompt-queue",
            "prompt680-multi-prompt-real-task-chain-acceptance",
            "prompt681-operational-readiness-gap-to-real-autonomous-development",
            "prompt682-real-code-change-inside-multi-prompt-chain",
            "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain",
            "prompt684-release-docs-demo-pack-acceptance",
            "prompt685-new-safe-goal-operational-daemon-acceptance",
            "prompt686-live-codex-execution-or-runtime-boundary-acceptance",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_final_operational_completion_gate(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt687-test",
        )

    def test_prompt667_through_prompt686_baselines_are_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_final_gate_baselines(repo)
        for prompt in ["667", "671", "677", "679", "680", "681", "682", "683", "684", "685", "686"]:
            self.assertTrue(result[f"prompt{prompt}_verified"], msg=f"prompt{prompt}")

    def test_final_criteria_matrix_contains_required_criteria_and_counts(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            matrix = build_final_criteria_matrix(repo)
        ids = {item["id"] for item in matrix["criteria"]}
        self.assertEqual(matrix["total_final_criteria_count"], 17)
        self.assertEqual(matrix["proven_final_criteria_count"], 14)
        self.assertEqual(matrix["boundary_confirmed_criteria_count"], 2)
        self.assertEqual(matrix["unproven_final_criteria_count"], 0)
        self.assertEqual(matrix["false_by_evidence_criteria_count"], 1)
        for criterion in [
            "end_to_end_unattended_project_run",
            "extended_operational_soak_50_ticks",
            "multi_prompt_queue_7_items",
            "no_confirmation_profile_wired",
            "multi_prompt_real_task_chain_7_items",
            "operational_readiness_gap_analyzed",
            "real_code_change_inside_multi_prompt_chain",
            "bugfix_from_failing_test_inside_multi_prompt_chain",
            "release_docs_demo_pack",
            "new_safe_goal_operational_daemon",
            "live_codex_execution",
            "live_codex_runtime_boundary",
            "dry_run_only_boundary",
            "safety_gate_remote_destructive_secret_blocks",
            "no_false_completion_claims",
            "final_evidence_index",
            "final_operational_completion_gate",
        ]:
            self.assertIn(criterion, ids)

    def test_final_categories_match_prompt686_outcome_b(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        self.assertTrue(result["completed_as_local_only_bounded_autonomous_development_runner"])
        self.assertTrue(result["completed_as_dry_run_boundary_operational_runner"])
        self.assertFalse(result["completed_as_live_codex_no_human_autonomous_development_runner"])
        self.assertFalse(result["complete_as_real_no_human_autonomous_development"])
        self.assertFalse(result["live_codex_execution_proven_after"])
        self.assertTrue(result["live_codex_runtime_boundary_confirmed"])
        self.assertTrue(result["dry_run_only_boundary_confirmed"])
        self.assertEqual(result["runtime_boundary_reason"], RUNTIME_BOUNDARY_REASON)

    def test_remaining_blocker_and_required_action_are_preserved(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        self.assertEqual(result["remaining_blocker_1"], RUNTIME_BOUNDARY_REASON)
        self.assertIn("safe non-interactive workspace-write approval mode", result["required_next_action"])
        self.assertEqual(result["required_next_action"], REQUIRED_NEXT_ACTION)

    def test_false_completion_claims_and_abstract_language_are_rejected(self):
        valid = validate_completion_text(
            "complete_as_real_no_human_autonomous_development=false\n"
            "completed_as_live_codex_no_human_autonomous_development_runner=false\n"
        )
        invalid = validate_completion_text("fully complete and moving in the right direction")
        self.assertTrue(valid["false_completion_claims_rejected"])
        self.assertTrue(valid["no_abstract_only_progress_language_verified"])
        self.assertFalse(invalid["false_completion_claims_rejected"])
        self.assertFalse(invalid["no_abstract_only_progress_language_verified"])

    def test_acceptance_runner_writes_reports_matrix_and_docs(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            out = repo / "artifacts/autonomous_runtime"
            run_dir = out / "prompt687_final_operational_completion_gate"
            self.assertEqual(result["prompt687_status"], "success")
            self.assertTrue((repo / "docs/autonomous_runtime/final_operational_completion_gate.md").is_file())
            self.assertTrue((out / "prompt687_report.json").is_file())
            self.assertTrue((out / "prompt687_final_completion_matrix.json").is_file())
            self.assertTrue((run_dir / "baseline_verification.json").is_file())
            self.assertTrue((run_dir / "final_completion_categories.json").is_file())
            self.assertTrue((run_dir / "final_criteria_matrix.json").is_file())
            self.assertTrue((run_dir / "false_completion_guard.json").is_file())
            self.assertTrue((run_dir / "remaining_blockers.json").is_file())
            self.assertTrue((run_dir / "next_required_action.json").is_file())
            self.assertTrue((run_dir / "evidence_summary.json").is_file())
            self.assertTrue((run_dir / "final_gate_marker.json").is_file())

    def test_prior_prompt667_through_prompt686_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in range(667, 687)
                if n != 675
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in range(667, 687):
            expected = "not_present" if prompt == 675 else True
            self.assertEqual(result[f"prompt{prompt}_core_artifacts_preserved"], expected, msg=f"prompt{prompt}")


if __name__ == "__main__":
    unittest.main()

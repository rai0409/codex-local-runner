from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.manual_live_smoke_finalization import (
    EXPECTED_MARKER_CONTENT,
    MANUAL_EVIDENCE_DIR,
    REQUIRED_EVIDENCE_FILES,
    build_prompt688_final_matrix,
    run_manual_live_smoke_evidence_finalization,
    validate_manual_live_smoke_evidence,
    verify_prompt688_baselines,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ManualLiveSmokeFinalizationTests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt682_report.json",
            "artifacts/autonomous_runtime/prompt683_report.json",
            "artifacts/autonomous_runtime/prompt684_report.json",
            "artifacts/autonomous_runtime/prompt685_report.json",
            "artifacts/autonomous_runtime/prompt686_report.json",
            "artifacts/autonomous_runtime/prompt687_report.json",
            "artifacts/autonomous_runtime/prompt687_final_completion_matrix.json",
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        source_evidence = REPO_ROOT / MANUAL_EVIDENCE_DIR
        target_evidence = repo / MANUAL_EVIDENCE_DIR
        shutil.copytree(source_evidence, target_evidence)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
        )
        for tag in [
            "prompt682-real-code-change-inside-multi-prompt-chain",
            "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain",
            "prompt684-release-docs-demo-pack-acceptance",
            "prompt685-new-safe-goal-operational-daemon-acceptance",
            "prompt686-live-codex-execution-or-runtime-boundary-acceptance",
            "prompt687-final-operational-completion-gate",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_manual_live_smoke_evidence_finalization(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt688-test",
        )

    def test_prompt682_through_prompt687_baselines_are_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt688_baselines(repo)
        for prompt in ["682", "683", "684", "685", "686", "687"]:
            self.assertTrue(result[f"prompt{prompt}_verified"], msg=f"prompt{prompt}")

    def test_copied_manual_live_smoke_evidence_files_are_present(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = validate_manual_live_smoke_evidence(repo)
        self.assertTrue(result["manual_evidence_dir_exists"])
        self.assertEqual(result["manual_evidence_files_count"], len(REQUIRED_EVIDENCE_FILES))
        self.assertTrue(result["manual_required_evidence_files_present"])
        self.assertTrue(result["marker_content_valid"])
        self.assertTrue(result["manual_result_json_valid"])
        self.assertTrue(result["manual_result_live_smoke_attempted"])
        self.assertTrue(result["manual_result_live_smoke_succeeded"])
        self.assertEqual(result["manual_result_exit_code"], 0)
        self.assertEqual(result["manual_result_codex_exec_mode"], "workspace-write")
        self.assertTrue(result["manual_result_ephemeral"])
        self.assertTrue(result["manual_result_json_events"])
        self.assertFalse(result["manual_result_unexpected_tracked_file_diff"])
        self.assertTrue(result["codex_events_jsonl_non_empty"])
        self.assertTrue(result["manual_live_smoke_evidence_valid"])

    def test_invalid_marker_keeps_live_codex_execution_unproven(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            (repo / MANUAL_EVIDENCE_DIR / "live_smoke_marker.txt").write_text("WRONG\n", encoding="utf-8")
            validation = validate_manual_live_smoke_evidence(repo)
            matrix = build_prompt688_final_matrix(validation["manual_live_smoke_evidence_valid"])
        self.assertFalse(validation["marker_content_valid"])
        self.assertFalse(matrix["live_codex_execution_proven_after"])
        self.assertFalse(matrix["complete_as_real_no_human_autonomous_development"])
        self.assertEqual(matrix["remaining_blockers"][0]["blocker"], "manual live smoke evidence invalid")

    def test_invalid_manual_result_keeps_live_codex_execution_unproven(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            (repo / MANUAL_EVIDENCE_DIR / "manual_result.json").write_text('{"live_smoke_succeeded": false}\n', encoding="utf-8")
            validation = validate_manual_live_smoke_evidence(repo)
            matrix = build_prompt688_final_matrix(validation["manual_live_smoke_evidence_valid"])
        self.assertFalse(validation["manual_result_live_smoke_succeeded"])
        self.assertFalse(matrix["live_codex_execution_proven_after"])
        self.assertFalse(matrix["completed_as_live_codex_no_human_autonomous_development_runner"])

    def test_valid_evidence_sets_live_completion_categories_true(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
        self.assertEqual(result["prompt688_status"], "success")
        self.assertTrue(result["live_codex_execution_proven_after"])
        self.assertFalse(result["live_codex_runtime_boundary_confirmed"])
        self.assertFalse(result["dry_run_only_boundary_confirmed"])
        self.assertTrue(result["completed_as_local_only_bounded_autonomous_development_runner"])
        self.assertTrue(result["completed_as_dry_run_boundary_operational_runner"])
        self.assertTrue(result["completed_as_live_codex_no_human_autonomous_development_runner"])
        self.assertTrue(result["complete_as_real_no_human_autonomous_development"])
        self.assertEqual(result["total_final_criteria_count"], 17)
        self.assertEqual(result["proven_final_criteria_count"], 17)
        self.assertEqual(result["boundary_confirmed_criteria_count"], 0)
        self.assertEqual(result["unproven_final_criteria_count"], 0)
        self.assertEqual(result["false_by_evidence_criteria_count"], 0)
        self.assertEqual(result["remaining_blocker_count"], 0)
        self.assertIsNone(result["remaining_blocker_1"])

    def test_valid_evidence_writes_expected_reports(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            self._run(repo)
            out = repo / "artifacts/autonomous_runtime"
            run_dir = out / "prompt688_manual_live_smoke_finalization"
            self.assertTrue((out / "prompt688_report.json").is_file())
            self.assertTrue((out / "prompt688_final_completion_matrix.json").is_file())
            self.assertTrue((run_dir / "baseline_verification.json").is_file())
            self.assertTrue((run_dir / "manual_smoke_evidence_validation.json").is_file())
            self.assertTrue((run_dir / "final_completion_categories.json").is_file())
            self.assertTrue((run_dir / "final_criteria_matrix.json").is_file())
            self.assertTrue((run_dir / "remaining_blockers.json").is_file())
            self.assertTrue((run_dir / "evidence_summary.json").is_file())
            self.assertTrue((run_dir / "finalization_marker.json").is_file())

    def test_prior_prompt667_through_prompt687_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in range(667, 688)
                if n != 675
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in range(667, 688):
            expected = "not_present" if prompt == 675 else True
            self.assertEqual(result[f"prompt{prompt}_core_artifacts_preserved"], expected, msg=f"prompt{prompt}")

    def test_marker_content_constant_matches_prompt_requirement(self):
        self.assertEqual(EXPECTED_MARKER_CONTENT, "PROMPT688_LIVE_CODEX_SMOKE_OK")


if __name__ == "__main__":
    unittest.main()

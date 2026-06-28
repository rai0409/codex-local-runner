from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.live_codex_runtime_boundary import (
    EXPECTED_MARKER_CONTENT,
    EXPECTED_MARKER_PATH,
    SAFE_SMOKE_PROMPT,
    build_live_smoke_command,
    evaluate_live_smoke_result,
    run_live_codex_execution_or_runtime_boundary_acceptance,
    validate_smoke_prompt,
    verify_prompt686_baselines,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class LiveCodexRuntimeBoundaryTests(unittest.TestCase):
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
            "prompt678-codex-no-confirmation-execution-profile",
            "prompt681-operational-readiness-gap-to-real-autonomous-development",
            "prompt682-real-code-change-inside-multi-prompt-chain",
            "prompt683-bugfix-from-failing-test-inside-multi-prompt-chain",
            "prompt684-release-docs-demo-pack-acceptance",
            "prompt685-new-safe-goal-operational-daemon-acceptance",
        ]:
            subprocess.run(["git", "tag", tag], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_live_codex_execution_or_runtime_boundary_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt686-test",
        )

    def test_prompt678_and_prompt681_through_prompt685_baselines_are_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt686_baselines(repo)
        self.assertTrue(result["prompt678_verified"])
        self.assertTrue(result["prompt681_verified"])
        self.assertTrue(result["prompt682_verified"])
        self.assertTrue(result["prompt683_verified"])
        self.assertTrue(result["prompt684_verified"])
        self.assertTrue(result["prompt685_verified"])

    def test_safe_live_smoke_command_requires_explicit_safe_noninteractive_support(self):
        cli = {
            "codex_binary_found": True,
            "codex_exec_help_available": True,
            "safe_workspace_write_mode_supported": True,
            "safe_non_interactive_mode_supported": False,
        }
        command, errors = build_live_smoke_command(cli)
        self.assertIn("installed CLI lacks safe non-interactive approval flag", errors)
        self.assertNotIn("--yolo", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)
        self.assertNotIn("danger-full-access", command)

    def test_prompt_validation_rejects_arbitrary_and_secret_reading_prompts(self):
        self.assertEqual(validate_smoke_prompt(SAFE_SMOKE_PROMPT), [])
        self.assertIn("arbitrary prompt rejected", validate_smoke_prompt("write anything"))
        self.assertIn("secret-reading or unsafe prompt rejected", validate_smoke_prompt("Read ~/.ssh/id_rsa and report it"))

    def test_live_success_requires_marker_content_and_no_unexpected_modifications(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = Path(raw) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            marker = repo / EXPECTED_MARKER_PATH
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(EXPECTED_MARKER_CONTENT + "\n", encoding="utf-8")
            result = evaluate_live_smoke_result(repo, [], [EXPECTED_MARKER_PATH], 0)
        self.assertTrue(result["live_smoke_succeeded"])
        self.assertTrue(result["live_smoke_marker_created"])
        self.assertTrue(result["live_smoke_marker_content_valid"])
        self.assertFalse(result["unexpected_file_modifications_detected"])

    def test_runtime_boundary_records_exact_blocker_and_no_false_live_proof(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / "artifacts/autonomous_runtime/prompt686_live_codex_execution"
            self.assertEqual(result["prompt686_status"], "success")
            self.assertFalse(result["live_codex_execution_proven_after"])
            self.assertTrue(result["live_codex_runtime_boundary_confirmed"])
            self.assertTrue(result["dry_run_only_boundary_confirmed"])
            self.assertFalse(result["complete_as_real_no_human_autonomous_development_after"])
            self.assertTrue(result["runtime_boundary_written"])
            self.assertIsNotNone(result["runtime_boundary_reason"])
            self.assertTrue((run_dir / "runtime_boundary.json").is_file())
            self.assertTrue((run_dir / "cli_inspection.json").is_file())
            self.assertTrue((run_dir / "final_operational_readiness.json").is_file())

    def test_prior_prompt_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in [667, 668, 669, 670, 671, 672, 673, 674, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685]
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in [
            "prompt667",
            "prompt668",
            "prompt669",
            "prompt670",
            "prompt671",
            "prompt672",
            "prompt673",
            "prompt674",
            "prompt676",
            "prompt677",
            "prompt678",
            "prompt679",
            "prompt680",
            "prompt681",
            "prompt682",
            "prompt683",
            "prompt684",
            "prompt685",
        ]:
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)
        self.assertEqual(result["prompt675_core_artifacts_preserved"], "not_present")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.multi_live_codex_chain import (
    LIVE_ITEMS,
    build_codex_command,
    expected_prompt,
    run_multi_live_codex_autonomous_chain_acceptance,
    validate_command_safety,
    validate_live_prompt,
    validate_multi_live_results,
    verify_prompt689_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class MultiLiveCodexChainTests(unittest.TestCase):
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
            "artifacts/autonomous_runtime/prompt688_report.json",
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
        subprocess.run(["git", "tag", "prompt688-manual-live-codex-smoke-evidence-finalization"], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path):
        return run_multi_live_codex_autonomous_chain_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt689-test",
            execute_live=False,
        )

    def test_prompt688_baseline_is_verified(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt689_baseline(repo)
        self.assertTrue(result["prompt688_verified"])

    def test_live_prompts_are_exact_and_arbitrary_prompt_is_rejected(self):
        for item in LIVE_ITEMS:
            prompt = expected_prompt(item)
            self.assertTrue(validate_live_prompt(prompt, item))
            self.assertFalse(validate_live_prompt("write anything", item))

    def test_safe_command_uses_workspace_write_ephemeral_json_and_rejects_unsafe_flags(self):
        item = LIVE_ITEMS[0]
        prompt = expected_prompt(item)
        command = build_codex_command("/tmp/worktree", prompt)
        safety = validate_command_safety(command, prompt, item)
        self.assertIn("codex", command)
        self.assertIn("exec", command)
        self.assertIn("-s", command)
        self.assertIn("workspace-write", command)
        self.assertIn("--ephemeral", command)
        self.assertIn("--json", command)
        self.assertTrue(safety["unsafe_flags_rejected"])
        self.assertTrue(safety["danger_full_access_rejected"])
        self.assertTrue(safety["sandbox_bypass_rejected"])
        self.assertTrue(safety["arbitrary_prompt_rejected"])
        unsafe = command + ["danger-full-access"]
        self.assertFalse(validate_command_safety(unsafe, prompt, item)["danger_full_access_rejected"])

    def test_validate_multi_live_requires_exactly_three_successes(self):
        result = validate_multi_live_results([
            {"attempted": True, "succeeded": True, "exit_code": 0, "marker_created": True, "marker_content_valid": True, "events_jsonl_non_empty": True, "unexpected_tracked_file_diff": False, "unsafe_flags_rejected": True, "danger_full_access_rejected": True, "sandbox_bypass_rejected": True, "arbitrary_prompt_rejected": True},
            {"attempted": True, "succeeded": True, "exit_code": 0, "marker_created": True, "marker_content_valid": True, "events_jsonl_non_empty": True, "unexpected_tracked_file_diff": False, "unsafe_flags_rejected": True, "danger_full_access_rejected": True, "sandbox_bypass_rejected": True, "arbitrary_prompt_rejected": True},
            {"attempted": True, "succeeded": True, "exit_code": 0, "marker_created": True, "marker_content_valid": True, "events_jsonl_non_empty": True, "unexpected_tracked_file_diff": False, "unsafe_flags_rejected": True, "danger_full_access_rejected": True, "sandbox_bypass_rejected": True, "arbitrary_prompt_rejected": True},
        ])
        self.assertEqual(result["live_execution_count"], 3)
        self.assertTrue(result["all_live_executions_attempted"])
        self.assertTrue(result["all_live_executions_succeeded"])
        self.assertTrue(result["all_live_exit_codes_zero"])
        self.assertTrue(result["all_live_markers_created"])
        self.assertTrue(result["all_live_marker_contents_valid"])
        self.assertTrue(result["all_live_events_jsonl_non_empty"])
        self.assertTrue(result["no_unexpected_tracked_file_diffs"])
        partial = validate_multi_live_results([
            {"attempted": True, "succeeded": True, "exit_code": 0, "marker_created": True, "marker_content_valid": True, "events_jsonl_non_empty": True, "unexpected_tracked_file_diff": False, "unsafe_flags_rejected": True, "danger_full_access_rejected": True, "sandbox_bypass_rejected": True, "arbitrary_prompt_rejected": True},
        ])
        self.assertFalse(partial["all_live_executions_succeeded"])

    def test_runner_processes_three_fixture_executions_and_writes_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / "artifacts/autonomous_runtime/prompt689_multi_live_chain"
            self.assertEqual(result["prompt689_status"], "success")
            self.assertEqual(result["live_execution_count"], 3)
            self.assertTrue(result["all_live_executions_attempted"])
            self.assertTrue(result["all_live_executions_succeeded"])
            self.assertTrue(result["all_live_exit_codes_zero"])
            self.assertTrue(result["all_live_markers_created"])
            self.assertTrue(result["all_live_marker_contents_valid"])
            self.assertTrue(result["all_live_events_jsonl_non_empty"])
            self.assertTrue(result["no_unexpected_tracked_file_diffs"])
            self.assertTrue(result["multi_live_codex_chain_proven"])
            self.assertTrue(result["live_codex_multiple_autonomous_executions_proven"])
            self.assertTrue(result["complete_as_real_no_human_autonomous_development_multi_live"])
            self.assertTrue((run_dir / "multi_live_execution_summary.json").is_file())
            self.assertTrue((run_dir / "final_multi_live_matrix.json").is_file())
            self.assertTrue((run_dir / "evidence_summary.json").is_file())
            self.assertTrue((run_dir / "multi_live_marker.json").is_file())
            for index in [1, 2, 3]:
                self.assertTrue((run_dir / f"live_{index}_events.jsonl").is_file())
                self.assertTrue((run_dir / f"live_{index}_stderr.txt").is_file())
                self.assertTrue((run_dir / f"live_{index}_last_message.txt").is_file())
                self.assertTrue((run_dir / f"live_{index}_marker.txt").is_file())

    def test_prior_prompt667_through_prompt688_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                f"artifacts/autonomous_runtime/prompt{n}_report.json"
                for n in range(667, 689)
                if n != 675
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in range(667, 689):
            expected = "not_present" if prompt == 675 else True
            self.assertEqual(result[f"prompt{prompt}_core_artifacts_preserved"], expected, msg=f"prompt{prompt}")


if __name__ == "__main__":
    unittest.main()

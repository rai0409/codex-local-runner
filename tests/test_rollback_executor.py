from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.rollback_executor import execute_constrained_rollback


class RollbackExecutorTests(unittest.TestCase):
    def _run_git(self, repo_dir: str, args: list[str]) -> str:
        proc = subprocess.run(
            ["git", "-C", repo_dir, *args],
            check=True,
            text=True,
            capture_output=True,
        )
        return proc.stdout.strip()

    def _git_commit(self, repo_dir: str, message: str) -> None:
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "-m",
                message,
            ],
        )

    def _init_merged_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])

        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        pre_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        self._run_git(
            repo_dir,
            [
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "merge",
                "--no-ff",
                "--no-edit",
                source_sha,
            ],
        )
        post_merge_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        return {
            "target_ref": "refs/heads/main",
            "pre_merge_sha": pre_merge_sha,
            "post_merge_sha": post_merge_sha,
        }

    def test_constrained_rollback_succeeds_when_state_matches_trace(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)

            result = execute_constrained_rollback(
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["attempted"])
        self.assertTrue(result["consistency_check_passed"])
        self.assertEqual(result["current_head_sha"], trace["post_merge_sha"])
        self.assertEqual(result["rollback_result_sha"], head_after)
        self.assertIsNone(result["error"])

    def test_constrained_rollback_skips_when_current_head_mismatches_trace(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            (Path(repo_dir) / "extra.txt").write_text("extra\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "extra.txt"])
            self._git_commit(repo_dir, "drift")

            result = execute_constrained_rollback(
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["attempted"])
        self.assertFalse(result["consistency_check_passed"])
        self.assertEqual(result["error"], "current_head_mismatch_post_merge")

    def test_constrained_rollback_skips_when_target_ref_drifts(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            trace = self._init_merged_repo(repo_dir)
            # Move away from target ref and ensure drift is detected safely as non-attempt.
            self._run_git(repo_dir, ["checkout", "-b", "other"])
            (Path(repo_dir) / "other.txt").write_text("other\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "other.txt"])
            self._git_commit(repo_dir, "other branch change")
            result = execute_constrained_rollback(
                repo_path=repo_dir,
                target_ref=trace["target_ref"],
                pre_merge_sha=trace["pre_merge_sha"],
                post_merge_sha=trace["post_merge_sha"],
            )

        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["attempted"])
        self.assertEqual(result["error"], "target_ref_drift_detected")


if __name__ == "__main__":
    unittest.main()

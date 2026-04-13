from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.merge_executor import execute_constrained_merge


class MergeExecutorTests(unittest.TestCase):
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

    def _init_mergeable_repo(self, repo_dir: str) -> dict[str, str]:
        self._run_git(repo_dir, ["init"])
        self._run_git(repo_dir, ["checkout", "-b", "main"])
        (Path(repo_dir) / "README.md").write_text("base\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "README.md"])
        self._git_commit(repo_dir, "base")
        base_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "-b", "feature"])
        (Path(repo_dir) / "feature.txt").write_text("feature\n", encoding="utf-8")
        self._run_git(repo_dir, ["add", "feature.txt"])
        self._git_commit(repo_dir, "feature")
        source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self._run_git(repo_dir, ["checkout", "main"])
        return {
            "target_ref": "refs/heads/main",
            "base_sha": base_sha,
            "source_sha": source_sha,
        }

    def test_constrained_merge_succeeds_with_matching_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            identity = self._init_mergeable_repo(repo_dir)

            result = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha=identity["base_sha"],
            )

            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["attempted"])
        self.assertEqual(result["pre_merge_sha"], identity["base_sha"])
        self.assertEqual(result["post_merge_sha"], head_after)
        self.assertEqual(result["merge_result_sha"], head_after)
        self.assertIsNone(result["error"])

    def test_constrained_merge_is_skipped_on_base_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            identity = self._init_mergeable_repo(repo_dir)

            result = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha="0" * 40,
            )

        self.assertEqual(result["status"], "skipped")
        self.assertFalse(result["attempted"])
        self.assertEqual(result["error"], "base_sha_mismatch")

    def test_constrained_merge_is_skipped_when_source_already_merged(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            identity = self._init_mergeable_repo(repo_dir)
            first = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha=identity["base_sha"],
            )
            head_after_first = self._run_git(repo_dir, ["rev-parse", "HEAD"])

            second = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref=identity["target_ref"],
                source_sha=identity["source_sha"],
                base_sha=head_after_first,
            )

        self.assertEqual(first["status"], "succeeded")
        self.assertEqual(second["status"], "skipped")
        self.assertFalse(second["attempted"])
        self.assertEqual(second["error"], "source_already_merged_into_target")

    def test_constrained_merge_fails_on_conflict_and_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir:
            self._run_git(repo_dir, ["init"])
            self._run_git(repo_dir, ["checkout", "-b", "main"])
            file_path = Path(repo_dir) / "conflict.txt"
            file_path.write_text("base\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "conflict.txt"])
            self._git_commit(repo_dir, "base")

            self._run_git(repo_dir, ["checkout", "-b", "feature"])
            file_path.write_text("feature\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "conflict.txt"])
            self._git_commit(repo_dir, "feature change")
            source_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

            self._run_git(repo_dir, ["checkout", "main"])
            file_path.write_text("main\n", encoding="utf-8")
            self._run_git(repo_dir, ["add", "conflict.txt"])
            self._git_commit(repo_dir, "main change")
            base_sha = self._run_git(repo_dir, ["rev-parse", "HEAD"])

            result = execute_constrained_merge(
                repo_path=repo_dir,
                target_ref="refs/heads/main",
                source_sha=source_sha,
                base_sha=base_sha,
            )
            head_after = self._run_git(repo_dir, ["rev-parse", "HEAD"])

        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["attempted"])
        self.assertEqual(result["pre_merge_sha"], base_sha)
        self.assertEqual(result["post_merge_sha"], head_after)
        self.assertIsNone(result["merge_result_sha"])
        self.assertTrue(bool(result["error"]))


if __name__ == "__main__":
    unittest.main()

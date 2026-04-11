from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from workspace.worktree import cleanup_git_worktree
from workspace.worktree import prepare_git_worktree


class WorktreePreparationTests(unittest.TestCase):
    def _run(self, cmd: list[str]) -> None:
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    def _init_git_repo_with_commit(self, repo_dir: str) -> None:
        self._run(["git", "-C", repo_dir, "init"])
        self._run(
            [
                "git",
                "-C",
                repo_dir,
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "init",
            ]
        )

    def test_prepare_git_worktree_success(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as parent_dir:
            self._init_git_repo_with_commit(repo_dir)

            result = prepare_git_worktree(
                source_repo_path=repo_dir,
                worktree_parent=parent_dir,
            )

            self.assertEqual(
                set(result.keys()),
                {
                    "source_repo_path",
                    "worktree_path",
                    "branch_name",
                    "created",
                    "cleanup_needed",
                    "error",
                },
            )
            self.assertTrue(result["created"])
            self.assertTrue(result["cleanup_needed"])
            self.assertNotEqual(result["worktree_path"], "")
            self.assertNotEqual(result["branch_name"], "")
            self.assertEqual(result["error"], "")
            self.assertTrue(Path(result["worktree_path"]).exists())

            cleanup = cleanup_git_worktree(
                source_repo_path=repo_dir,
                worktree_path=result["worktree_path"],
                branch_name=result["branch_name"],
            )
            self.assertTrue(cleanup["cleaned"], cleanup["error"])
            self.assertFalse(Path(result["worktree_path"]).exists())

    def test_prepare_git_worktree_fails_for_non_git_repo(self) -> None:
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as parent_dir:
            result = prepare_git_worktree(
                source_repo_path=repo_dir,
                worktree_parent=parent_dir,
            )

        self.assertFalse(result["created"])
        self.assertFalse(result["cleanup_needed"])
        self.assertEqual(result["worktree_path"], "")
        self.assertEqual(result["branch_name"], "")
        self.assertIn("not a git working tree", result["error"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.sandbox_cleanup import (
    cleanup_generated_python_artifacts,
    evaluate_sandbox_cleanliness,
)


def _make_sandbox(tmp_dir: Path) -> Path:
    repo = tmp_dir / "sandbox_repo"
    repo.mkdir()
    (repo / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (repo / "notes.md").write_text("# notes\n", encoding="utf-8")
    (repo / "data.json").write_text("{}\n", encoding="utf-8")
    return repo


def _add_generated_artifacts(repo: Path) -> None:
    cache = repo / "__pycache__"
    cache.mkdir()
    (cache / "calculator.cpython-312.pyc").write_bytes(b"\x00")
    nested = repo / "pkg" / "__pycache__"
    nested.mkdir(parents=True)
    (nested / "mod.cpython-312.pyc").write_bytes(b"\x00")
    (repo / "stray.pyc").write_bytes(b"\x00")
    (repo / "legacy.pyo").write_bytes(b"\x00")


class CleanupRemovalTests(unittest.TestCase):
    def test_removes_pycache_pyc_and_pyo_preserving_sources(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_sandbox(tmp_dir)
            _add_generated_artifacts(repo)
            result = cleanup_generated_python_artifacts(repo)
            remaining = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file())
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["removed_count"], 4)
        self.assertIn("__pycache__/", result["removed_paths"])
        self.assertIn("pkg/__pycache__/", result["removed_paths"])
        self.assertIn("stray.pyc", result["removed_paths"])
        self.assertIn("legacy.pyo", result["removed_paths"])
        self.assertEqual(remaining, ["calculator.py", "data.json", "notes.md"])

    def test_noop_on_clean_repo(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = _make_sandbox(Path(raw))
            result = cleanup_generated_python_artifacts(repo)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["removed_count"], 0)


class CleanupPathSafetyTests(unittest.TestCase):
    def test_refuses_empty_path(self):
        for value in ("", None, "   "):
            result = cleanup_generated_python_artifacts(value)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["blocked_reason"], "empty_path")

    def test_refuses_root(self):
        result = cleanup_generated_python_artifacts("/")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "root_path")

    def test_refuses_main_repo_and_non_tmp_paths(self):
        main_repo = Path(__file__).resolve().parents[1]
        result = cleanup_generated_python_artifacts(main_repo)
        self.assertEqual(result["status"], "blocked")
        self.assertIn(result["blocked_reason"], {"path_not_sandbox", "main_repo_path"})
        result_home = cleanup_generated_python_artifacts(str(Path.home()))
        self.assertEqual(result_home["status"], "blocked")
        self.assertEqual(result_home["blocked_reason"], "path_not_sandbox")

    def test_refuses_symlink_escaping_tmp(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            link = Path(raw) / "escape"
            link.symlink_to(Path(__file__).resolve().parents[1])
            result = cleanup_generated_python_artifacts(link)
        self.assertEqual(result["status"], "blocked")
        self.assertIn(result["blocked_reason"], {"path_not_sandbox", "main_repo_path"})

    def test_refuses_missing_directory(self):
        result = cleanup_generated_python_artifacts("/tmp/does-not-exist-prompt637")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "path_not_directory")


class SandboxCleanlinessTests(unittest.TestCase):
    def _git_repo(self, tmp_dir: Path) -> Path:
        repo = _make_sandbox(tmp_dir)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=t@l", "-c", "user.name=t", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        return repo

    def test_dirty_when_untracked_file_remains(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._git_repo(Path(raw))
            (repo / "__pycache__").mkdir()
            (repo / "__pycache__" / "x.pyc").write_bytes(b"\x00")
            state = evaluate_sandbox_cleanliness(repo)
        self.assertFalse(state["sandbox_final_status_clean"])
        self.assertEqual(state["sandbox_untracked_after_cleanup"], ["__pycache__/"])

    def test_clean_after_artifacts_removed(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._git_repo(Path(raw))
            (repo / "__pycache__").mkdir()
            (repo / "__pycache__" / "x.pyc").write_bytes(b"\x00")
            cleanup_generated_python_artifacts(repo)
            state = evaluate_sandbox_cleanliness(repo)
        self.assertTrue(state["sandbox_final_status_clean"])
        self.assertEqual(state["sandbox_final_status_short"], [])


if __name__ == "__main__":
    unittest.main()

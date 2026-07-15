from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.commit_tag import (
    SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
    execute_sandbox_commit_tag,
)


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def _make_repo(tmp_dir: Path) -> Path:
    repo = tmp_dir / "sandbox_repo"
    repo.mkdir()
    (repo / "calculator.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    _git(["init", "-q"], cwd=repo)
    _git(["add", "."], cwd=repo)
    _git(["-c", "user.email=t@local", "-c", "user.name=t", "commit", "-q", "-m", "fixture"], cwd=repo)
    return repo


def _modify(repo: Path, rel: str = "calculator.py") -> None:
    target = repo / rel
    target.write_text(target.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")


def _run(repo: Path, tmp_dir: Path, **overrides):
    kwargs = dict(
        repo_path=repo,
        allowed_files=["calculator.py"],
        artifact_dir=tmp_dir / "artifacts",
        task_id="unit-task",
        enabled=True,
        explicit_enable_token=SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
    )
    kwargs.update(overrides)
    return execute_sandbox_commit_tag(**kwargs)


class SandboxCommitTagGateTests(unittest.TestCase):
    def test_success_commits_and_tags_in_sandbox(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            _modify(repo)
            result = _run(repo, tmp_dir)
            log_count = len(_git(["log", "--oneline"], cwd=repo).splitlines())
            tags = _git(["tag"], cwd=repo).split()
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["commit_performed"])
        self.assertTrue(result["tag_performed"])
        self.assertTrue(result["commit_sha"])
        self.assertEqual(log_count, 2)
        self.assertEqual(tags, ["sandbox-unit-task"])

    def test_refuses_without_token(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            _modify(repo)
            result = _run(repo, tmp_dir, explicit_enable_token="wrong")
            log_count = len(_git(["log", "--oneline"], cwd=repo).splitlines())
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "explicit_enable_required")
        self.assertEqual(log_count, 1)

    def test_refuses_changes_outside_allowlist(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            _modify(repo)
            (repo / "rogue.py").write_text("x = 1\n", encoding="utf-8")
            result = _run(repo, tmp_dir)
            log_count = len(_git(["log", "--oneline"], cwd=repo).splitlines())
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "changes_outside_allowed_files")
        self.assertIn("rogue.py", result["changes_outside_allowed_files"])
        self.assertEqual(log_count, 1)

    def test_refuses_forbidden_path(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            _modify(repo)
            (repo / "secrets.txt").write_text("nope\n", encoding="utf-8")
            result = _run(
                repo,
                tmp_dir,
                allowed_files=["calculator.py", "secrets.txt"],
                forbidden_paths=["secrets.txt"],
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "forbidden_path_present")

    def test_refuses_existing_tag(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            _git(["tag", "sandbox-unit-task"], cwd=repo)
            _modify(repo)
            result = _run(repo, tmp_dir)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "tag_already_exists")

    def test_refuses_non_tmp_repo_and_main_repo(self):
        main_repo = Path(__file__).resolve().parents[1]
        result = execute_sandbox_commit_tag(
            repo_path=main_repo,
            allowed_files=["anything.py"],
            artifact_dir="/tmp/sandbox_commit_tag_refusal_artifacts",
            enabled=True,
            explicit_enable_token=SANDBOX_COMMIT_TAG_ENABLE_TOKEN,
        )
        self.assertEqual(result["status"], "blocked")
        self.assertIn(result["blocked_reason"], {"repo_not_sandbox", "repo_is_main_repo"})
        self.assertFalse(result["executed"])

    def test_pycache_is_ignored_not_blocking(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            _modify(repo)
            cache_dir = repo / "__pycache__"
            cache_dir.mkdir()
            (cache_dir / "calculator.cpython-312.pyc").write_text("x", encoding="utf-8")
            result = _run(repo, tmp_dir)
            tags = _git(["tag"], cwd=repo).split()
            committed = _git(["show", "--stat", "--name-only", "HEAD"], cwd=repo)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["ignored_generated_paths"], ["__pycache__/"])
        self.assertEqual(tags, ["sandbox-unit-task"])
        self.assertNotIn("__pycache__", committed)

    def test_refuses_when_no_changes(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            tmp_dir = Path(raw)
            repo = _make_repo(tmp_dir)
            result = _run(repo, tmp_dir)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_reason"], "no_changes_to_commit")


if __name__ == "__main__":
    unittest.main()

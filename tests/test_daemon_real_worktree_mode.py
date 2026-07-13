from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import run_task_queue_daemon as daemon  # noqa: E402

from automation.orchestration.planned_runner.daemon_queue import (  # noqa: E402
    enqueue_task,
    list_tasks,
)
from automation.orchestration.planned_runner.sandbox_cleanup import (  # noqa: E402
    cleanup_generated_python_artifacts,
)


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "user.email=t@local", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _make_repo(root: Path) -> Path:
    repo = root / "target_repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "target.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "universe.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests" / "test_universe.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _enqueue(queue_dir: Path, repo: Path, task_id: str) -> None:
    enqueue_task(
        queue_dir,
        {
            "task_id": task_id,
            "kind": "add_function",
            "repo_path": repo.as_posix(),
            "target_file": "target.py",
            "function_name": "added_fn",
            "expression": "a + b",
        },
    )


def _argv(
    root: Path,
    *,
    target_repo_mode: str | None = None,
    sandbox_commit_tag: bool = False,
) -> list[str]:
    argv = [
        "--queue-dir", (root / "queue").as_posix(),
        "--runs-dir", (root / "runs").as_posix(),
        "--work-dir", (root / "work").as_posix(),
        "--max-jobs", "1",
        "--max-cycles", "1",
        "--max-fix-attempts", "1",
    ]
    if target_repo_mode is not None:
        argv.extend(["--target-repo-mode", target_repo_mode])
    if sandbox_commit_tag:
        argv.append("--sandbox-commit-tag")
    return argv


def _resolved_retry(*, effect_spec_path, out_dir, **_kwargs):
    spec = json.loads(Path(effect_spec_path).read_text(encoding="utf-8"))
    repo = Path(spec["repo_path"])
    target = repo / spec["expected_modified_files"][0]
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\ndef added_fn(a, b):\n    return a + b\n",
        encoding="utf-8",
    )
    pycache = repo / "__pycache__"
    pycache.mkdir(exist_ok=True)
    (pycache / "generated.pyc").write_bytes(b"bytecode")
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "targeted_fix_retry_state.json").write_text("{}", encoding="utf-8")
    return {
        "status": "success",
        "converged": True,
        "stop_reason": "fix_attempt_succeeded",
        "fix_attempts_used": 1,
        "codex_invoked_count": 2,
        "attempts": [
            {"effect_verification_status": "failed", "failure_digest_path": ""},
            {"effect_verification_status": "passed", "failure_digest_path": ""},
        ],
    }


def _resolved_multi_scope_retry(*, effect_spec_path, out_dir, **_kwargs):
    spec = json.loads(Path(effect_spec_path).read_text(encoding="utf-8"))
    repo = Path(spec["repo_path"])
    (repo / "src" / "universe.py").write_text(
        "def load_universe(path):\n    return path\n", encoding="utf-8"
    )
    (repo / "tests" / "test_universe.py").write_text(
        "def test_load_universe():\n    assert True\n", encoding="utf-8"
    )
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "targeted_fix_retry_state.json").write_text("{}", encoding="utf-8")
    return {
        "status": "success",
        "converged": True,
        "stop_reason": "first_attempt_succeeded",
        "fix_attempts_used": 0,
        "codex_invoked_count": 1,
        "attempts": [{"effect_verification_status": "passed", "failure_digest_path": ""}],
    }


class DaemonRealWorktreeModeTests(unittest.TestCase):
    def test_default_sandbox_mode_still_runs_sandbox_cleanup(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            repo = _make_repo(root)
            _enqueue(root / "queue", repo, "sandbox-default")

            with mock.patch.object(
                daemon,
                "cleanup_generated_python_artifacts",
                wraps=cleanup_generated_python_artifacts,
            ) as cleanup_spy, mock.patch.object(
                daemon,
                "run_targeted_fix_retry",
                new=_resolved_retry,
            ):
                code = daemon.main(_argv(root))

            self.assertEqual(code, 0)
            cleanup_spy.assert_called_once_with(repo.as_posix())
            report = json.loads(
                (root / "runs" / "sandbox-default" / "run_report.json").read_text()
            )
            self.assertEqual(report["target_repo_mode"], "sandbox")
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["stage"], "done")
            self.assertFalse((repo / "__pycache__").exists())

    def test_real_worktree_mode_skips_cleanup_and_can_succeed_dirty(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as raw:
            root = Path(raw)
            repo = _make_repo(root)
            _enqueue(root / "queue", repo, "real-success")

            with mock.patch.object(
                daemon,
                "run_targeted_fix_retry",
                new=_resolved_retry,
            ), mock.patch.object(
                daemon,
                "cleanup_generated_python_artifacts",
                side_effect=AssertionError("cleanup must not run in real-worktree mode"),
            ), mock.patch.object(
                daemon,
                "evaluate_sandbox_cleanliness",
                side_effect=AssertionError("sandbox cleanliness must not run in real-worktree mode"),
            ), mock.patch.object(
                daemon,
                "execute_sandbox_commit_tag",
                side_effect=AssertionError("sandbox commit/tag must not run in real-worktree mode"),
            ):
                code = daemon.main(_argv(root, target_repo_mode="real-worktree"))

            self.assertEqual(code, 0)
            report = json.loads(
                (root / "runs" / "real-success" / "run_report.json").read_text()
            )
            self.assertEqual(report["status"], "success")
            self.assertEqual(report["stage"], "done")
            self.assertEqual(report["target_repo_mode"], "real-worktree")
            self.assertTrue(report["effect_gate_passed"])
            self.assertTrue(report["targeted_fix_converged"])
            self.assertGreaterEqual(report["codex_invoked_count"], 1)
            self.assertTrue(report["sandbox_cleanup_skipped"])
            self.assertEqual(report["sandbox_cleanup_skip_reason"], "real_worktree_mode")
            self.assertEqual(report["sandbox_generated_artifacts_removed"], 0)
            self.assertEqual(report["sandbox_generated_artifact_paths_removed"], [])
            self.assertFalse(report["commit_performed"])
            self.assertFalse(report["tag_performed"])
            self.assertFalse(report["sandbox_commit_performed"])
            self.assertFalse(report["sandbox_tag_performed"])
            self.assertEqual(report.get("errors", []), [])
            self.assertTrue((repo / "__pycache__" / "generated.pyc").exists())
            self.assertEqual(_git(repo, "rev-list", "--count", "HEAD"), "1")
            self.assertIn("real-success.json", list_tasks(root / "queue")["done"])

    def test_real_worktree_mode_blocks_sandbox_commit_tag_request(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as raw:
            root = Path(raw)
            repo = _make_repo(root)
            _enqueue(root / "queue", repo, "real-commit-tag-blocked")

            with mock.patch.object(
                daemon,
                "run_targeted_fix_retry",
                new=_resolved_retry,
            ), mock.patch.object(
                daemon,
                "cleanup_generated_python_artifacts",
                side_effect=AssertionError("cleanup must not run in real-worktree mode"),
            ), mock.patch.object(
                daemon,
                "execute_sandbox_commit_tag",
                side_effect=AssertionError("sandbox commit/tag must not run in real-worktree mode"),
            ):
                code = daemon.main(
                    _argv(root, target_repo_mode="real-worktree", sandbox_commit_tag=True)
                )

            self.assertEqual(code, 1)
            report = json.loads(
                (root / "runs" / "real-commit-tag-blocked" / "run_report.json").read_text()
            )
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["stage"], "sandbox_commit_tag_blocked")
            self.assertEqual(report["target_repo_mode"], "real-worktree")
            self.assertIn("--target-repo-mode real-worktree", report["errors"][0])
            self.assertTrue(report["sandbox_cleanup_skipped"])
            self.assertFalse(report["commit_performed"])
            self.assertFalse(report["tag_performed"])
            self.assertFalse(report["sandbox_commit_performed"])
            self.assertFalse(report["sandbox_tag_performed"])
            self.assertEqual(_git(repo, "rev-list", "--count", "HEAD"), "1")
            self.assertEqual(_git(repo, "tag"), "")
            self.assertIn(
                "real-commit-tag-blocked.json",
                list_tasks(root / "queue")["failed"],
            )

    def test_real_worktree_multi_file_scope_is_reported_and_completes(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as raw:
            root = Path(raw)
            repo = _make_repo(root)
            enqueue_task(
                root / "queue",
                {
                    "task_id": "real-multi-scope",
                    "kind": "bounded_implementation",
                    "repo_path": repo.as_posix(),
                    "allowed_files": ["src/universe.py", "tests/test_universe.py"],
                    "goal": "Implement a validated universe loader.",
                    "required_behavior": ["Add the loader and its focused test."],
                    "prohibited_behavior": ["Do not modify unrelated files."],
                    "required_text": {
                        "src/universe.py": ["def load_universe"],
                        "tests/test_universe.py": ["def test_load_universe"],
                    },
                },
            )
            with mock.patch.object(
                daemon, "run_targeted_fix_retry", new=_resolved_multi_scope_retry
            ):
                code = daemon.main(_argv(root, target_repo_mode="real-worktree"))
            report = json.loads(
                (root / "runs" / "real-multi-scope" / "run_report.json").read_text()
            )
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["allowed_files"], ["src/universe.py", "tests/test_universe.py"])

    def test_daemon_source_has_no_remote_operation_commands(self):
        source = (REPO_ROOT / "scripts" / "run_task_queue_daemon.py").read_text(encoding="utf-8")
        forbidden_command_fragments = [
            '["git", "push"',
            '["gh", "pr"',
            '["git", "merge"',
            "github.com",
        ]
        for fragment in forbidden_command_fragments:
            self.assertNotIn(fragment, source)


if __name__ == "__main__":
    unittest.main()

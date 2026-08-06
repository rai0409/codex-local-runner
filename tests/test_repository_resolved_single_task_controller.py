from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.orchestration.repository_profile import APPROVAL_ACTIONS, FORBIDDEN_GIT_OPERATION_IDS
from automation.orchestration.repository_resolved_single_task_controller import (
    RepositorySingleTaskRunResult,
    repository_single_task_run_result_to_mapping,
    run_repository_single_task,
    serialize_repository_single_task_run_result,
)


PYTHON = str(Path("/home/rai/codex-local-runner/.venv/bin/python").resolve())


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)


class FakePreparedAdapter:
    name = "codex_cli"

    def __init__(self, action=None, *, reason="validation_passed", malformed=None) -> None:
        self.action = action
        self.reason = reason
        self.malformed = malformed
        self.calls = 0

    def execute_prepared_worktree(self, payload):
        self.calls += 1
        if self.action:
            self.action(Path(payload["worktree_path"]))
        if self.malformed == "verify":
            return {"status": "completed", "retry": {"attempted": False, "outcome": "not_attempted"}}
        if self.malformed == "retry":
            return {"status": "completed", "verify": {"status": "passed", "reason": "validation_passed", "safe_validation": {"status": "passed"}}}
        safe = "passed" if self.reason == "validation_passed" else "failed"
        return {"status": "completed", "verify": {"status": "passed" if self.reason in {"validation_passed", "validation_partial"} else "failed", "reason": self.reason, "safe_validation": {"status": safe}}, "retry": {"attempted": False, "outcome": "not_attempted"}}


class RepositoryResolvedSingleTaskControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.source.mkdir()
        git(self.source, "init", "-b", "main")
        git(self.source, "config", "user.name", "Controller Test")
        git(self.source, "config", "user.email", "controller-test@example.invalid")
        (self.source / "allowed.txt").write_text("before\n", encoding="utf-8")
        git(self.source, "add", "--", "allowed.txt")
        git(self.source, "commit", "-m", "Initial")
        self.head = git(self.source, "rev-parse", "HEAD").stdout.strip()
        self.registry = self.base / "repos.yaml"
        self.bindings = self.base / "bindings.json"
        self.profile = self.base / "profile.json"
        self.spec = self.base / "task.json"
        self.output = self.base / "output"
        self._write_configuration()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_configuration(self, *, approvals=None, maximum=2) -> None:
        boundary = {action: "automatic" for action in APPROVAL_ACTIONS}
        if approvals:
            boundary.update(approvals)
        commands = []
        for command_id, kind in (("focused", "focused"), ("related", "related_regression"), ("full", "full"), ("compile", "compile")):
            commands.append({"command_id": command_id, "kind": kind, "argv": [PYTHON, "-m", "py_compile", "allowed.txt"], "cwd": ".", "timeout_seconds": 30, "required": True, "stop_on_failure": True})
        commands.append({"command_id": "diff", "kind": "diff_check", "argv": ["git", "diff", "--check"], "cwd": ".", "timeout_seconds": 30, "required": True, "stop_on_failure": True})
        profile = {"schema_version": "1", "profile_id": "repo", "repository_root": str(self.source), "base_branch": "main", "python_executable": PYTHON, "validation_commands": commands, "artifact_requirements": [], "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS), "max_changed_files": maximum, "approval_boundary": boundary, "environment_allowlist": []}
        self.profile.write_text(json.dumps(profile), encoding="utf-8")
        self.registry.write_text(json.dumps({"version": 1, "repos": [{"name": "repo", "logical_role": "test"}]}), encoding="utf-8")
        self.bindings.write_text(json.dumps({"version": 1, "bindings": [{"repository_id": "repo", "profile_path": str(self.profile)}]}), encoding="utf-8")
        self.spec.write_text(json.dumps({"schema_version": "1", "task_id": "task-1", "expected_head_sha": self.head, "prompt": "PROMPT_SECRET_MARKER_8B71", "allowed_changed_paths": ["allowed.txt"], "commit_message": "Controller task"}), encoding="utf-8")

    def _run(self, adapter):
        return run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: adapter)

    @staticmethod
    def _modify(worktree: Path, name="allowed.txt") -> None:
        (worktree / name).write_text("after\n", encoding="utf-8")

    def test_success_performs_real_explicit_stage_commit_cleanup_and_receipt(self):
        adapter = FakePreparedAdapter(self._modify)
        module = __import__("automation.orchestration.repository_resolved_single_task_controller", fromlist=["_git"])
        original_git = module._git
        invocations = []
        def spy(root, *arguments):
            invocations.append(arguments)
            return original_git(root, *arguments)
        with patch("automation.orchestration.repository_resolved_single_task_controller._git", side_effect=spy):
            result = self._run(adapter)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.reason_code, "single_task.completed")
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(git(self.source, "rev-parse", "HEAD").stdout.strip(), self.head)
        self.assertEqual(git(self.source, "status", "--porcelain").stdout, "")
        self.assertFalse(Path(result.worktree_path).exists())
        commit = git(self.source, "rev-parse", result.task_branch).stdout.strip()
        self.assertEqual(commit, result.commit_sha)
        self.assertEqual(git(self.source, "rev-parse", f"{commit}^").stdout.strip(), self.head)
        self.assertEqual(git(self.source, "log", "-1", "--format=%s", commit).stdout.strip(), "Controller task")
        self.assertEqual(git(self.source, "diff-tree", "--no-commit-id", "--name-only", "-r", commit).stdout.splitlines(), ["allowed.txt"])
        self.assertIn(("add", "--", "allowed.txt"), invocations)
        self.assertNotIn(("add", "."), invocations)
        self.assertNotIn(("add", "-A"), invocations)
        self.assertNotIn(("add", "--all"), invocations)
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(set(receipt), {"schema_version", "run_id", "status", "reason_code", "detail_reason_code", "repository_id", "task_id", "task_spec_sha256", "source_repository_root", "profile_id", "profile_base_branch", "profile_max_changed_files", "approvals", "source_state_before", "source_state_after", "expected_head_sha", "worktree_path", "worktree_preserved", "task_branch", "adapter_name", "execution_status", "validation_status", "validation_reason", "retry_attempted", "retry_outcome", "changed_files", "allowed_changed_paths", "commit_created", "commit_sha", "commit_parent_sha", "commit_message", "worktree_cleanup_status", "artifact_paths", "started_at", "finished_at"})
        digest = hashlib.sha256(Path(result.receipt_path).read_bytes()).hexdigest()
        self.assertEqual(Path(result.receipt_sha256_path).read_text(encoding="utf-8"), f"{digest}  receipt.json\n")
        self.assertFalse(list(Path(result.receipt_path).parent.glob(".receipt-*.tmp")))
        self.assertNotIn("PROMPT_SECRET_MARKER_8B71", Path(result.receipt_path).read_text(encoding="utf-8"))

    def test_source_preflight_blocks_before_adapter(self):
        cases = {
            "dirty": lambda: (self.source / "allowed.txt").write_text("dirty\n", encoding="utf-8"),
            "staged": lambda: (self.source / "allowed.txt").write_text("staged\n", encoding="utf-8"),
            "untracked": lambda: (self.source / "unknown.txt").write_text("x\n", encoding="utf-8"),
            "head": lambda: self.spec.write_text(json.dumps({"schema_version":"1","task_id":"task-1","expected_head_sha":"0" * 40,"prompt":"p","allowed_changed_paths":["allowed.txt"],"commit_message":"Controller task"}), encoding="utf-8"),
            "approval": lambda: self._write_configuration(approvals={"commit": "human_required"}),
        }
        for name, setup in cases.items():
            with self.subTest(name=name):
                self.tearDown(); self.setUp()
                setup()
                if name == "staged":
                    git(self.source, "add", "--", "allowed.txt")
                adapter = FakePreparedAdapter(self._modify)
                result = self._run(adapter)
                self.assertEqual(result.status, "blocked")
                self.assertEqual(adapter.calls, 0)
                self.assertIsNone(result.worktree_path)

    def test_validation_and_malformed_result_preserve_dirty_worktree_without_commit(self):
        for label, adapter in (("partial", FakePreparedAdapter(self._modify, reason="validation_partial")), ("failed", FakePreparedAdapter(self._modify, reason="validation_failed")), ("executor", FakePreparedAdapter(self._modify, reason="safe_validation_executor_error")), ("missing_verify", FakePreparedAdapter(self._modify, malformed="verify")), ("missing_retry", FakePreparedAdapter(self._modify, malformed="retry"))):
            with self.subTest(label=label):
                self.tearDown(); self.setUp()
                result = self._run(adapter)
                self.assertEqual(result.status, "blocked")
                self.assertTrue(result.worktree_preserved)
                self.assertTrue(Path(result.worktree_path).exists())
                self.assertEqual(git(self.source, "rev-list", "--count", "main").stdout.strip(), "1")

    def test_codex_git_mutations_are_detected_and_preserved(self):
        def stage(worktree):
            self._modify(worktree); git(worktree, "add", "--", "allowed.txt")
        def branch(worktree):
            self._modify(worktree); git(worktree, "switch", "-c", "unexpected")
        def commit(worktree):
            self._modify(worktree); git(worktree, "add", "--", "allowed.txt"); git(worktree, "commit", "-m", "unexpected")
        for expected, action in (("single_task.codex.staged_changes", stage), ("single_task.codex.branch_changed", branch), ("single_task.codex.head_changed", commit)):
            with self.subTest(expected=expected):
                self.tearDown(); self.setUp()
                result = self._run(FakePreparedAdapter(action))
                self.assertEqual(result.reason_code, expected)
                self.assertTrue(result.worktree_preserved)
                self.assertEqual(git(self.source, "rev-parse", "HEAD").stdout.strip(), self.head)

    def test_scope_no_change_and_failures_do_not_commit(self):
        scenarios = [
            ("scope", FakePreparedAdapter(lambda worktree: self._modify(worktree, "outside.txt")), "single_task.changed_files.out_of_scope", True),
            ("limit", FakePreparedAdapter(lambda worktree: (self._modify(worktree), self._modify(worktree, "other.txt"))), "single_task.changed_files.limit_exceeded", True),
            ("none", FakePreparedAdapter(), "single_task.changed_files.none", False),
        ]
        for name, adapter, reason, preserved in scenarios:
            with self.subTest(name=name):
                self.tearDown(); self.setUp()
                if name == "limit": self._write_configuration(maximum=1)
                result = self._run(adapter)
                self.assertEqual(result.reason_code, reason)
                self.assertEqual(result.worktree_preserved, preserved)
                self.assertEqual(git(self.source, "rev-list", "--count", "main").stdout.strip(), "1")
                if not preserved: self.assertFalse(Path(result.worktree_path).exists())

    def test_cleanup_failure_and_source_change_do_not_complete(self):
        original_git = __import__("automation.orchestration.repository_resolved_single_task_controller", fromlist=["_git"])._git
        def cleanup_failure(root, *args):
            if args[:2] == ("worktree", "remove"):
                return subprocess.CompletedProcess(["git"], 1, "", "")
            return original_git(root, *args)
        with patch("automation.orchestration.repository_resolved_single_task_controller._git", side_effect=cleanup_failure):
            result = self._run(FakePreparedAdapter(self._modify))
        self.assertEqual(result.reason_code, "single_task.worktree.cleanup_failed")
        self.assertIsNotNone(result.commit_sha)
        self.assertTrue(result.worktree_preserved)
        self.tearDown(); self.setUp()
        def change_source(worktree):
            self._modify(worktree)
            (self.source / "source-dirty.txt").write_text("x\n", encoding="utf-8")
        result = self._run(FakePreparedAdapter(change_source))
        self.assertEqual(result.reason_code, "single_task.source.changed_during_run")
        self.assertNotEqual(result.status, "completed")

    def test_result_mapping_is_deterministic(self):
        result = RepositorySingleTaskRunResult("1", "run", "blocked", "single_task.changed_files.none", None, "repo", "task", "/tmp/repo", "main", "a" * 40, "a" * 40, "profile", "b" * 64, "/tmp/work", False, None, None, None, (), "codex_cli", "completed", "passed", "validation_passed", False, "not_attempted", "/tmp/r", "/tmp/s", "start", "finish")
        self.assertEqual(repository_single_task_run_result_to_mapping(result)["changed_files"], [])
        self.assertEqual(serialize_repository_single_task_run_result(result), serialize_repository_single_task_run_result(result))

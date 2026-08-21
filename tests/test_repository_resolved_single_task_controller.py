from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
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
from automation.orchestration.repository_single_task_spec import RepositorySingleTaskSpec, serialize_repository_single_task_spec


PYTHON = str(Path(sys.executable).resolve())


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=True)


class FakePreparedAdapter:
    name = "codex_cli"

    def __init__(self, action=None, *, reason="validation_passed", malformed=None) -> None:
        self.action = action
        self.reason = reason
        self.malformed = malformed
        self.calls = 0
        self.payloads = []

    def execute_prepared_worktree(self, payload):
        self.calls += 1
        self.payloads.append(payload)
        if self.action:
            self.action(Path(payload["worktree_path"]))
        if self.malformed == "verify":
            return {"status": "completed", "retry": {"attempted": False, "outcome": "not_attempted"}}
        if self.malformed == "retry":
            return {"status": "completed", "verify": {"status": "passed", "reason": "validation_passed", "safe_validation": {"status": "passed"}}}
        safe = "passed" if self.reason == "validation_passed" else "failed"
        return {"status": "completed", "verify": {"status": "passed" if self.reason in {"validation_passed", "validation_partial"} else "failed", "reason": self.reason, "safe_validation": {"status": safe}}, "retry": {"attempted": False, "outcome": "not_attempted"}}


class RepairPreparedAdapter(FakePreparedAdapter):
    def __init__(self, action, *, exhausted=False):
        super().__init__(action)
        self.exhausted = exhausted
        self.payload = None

    def execute_prepared_worktree(self, payload):
        self.payload = payload
        self.calls += 1
        self.action(Path(payload["worktree_path"]))
        safe = "failed" if self.exhausted else "passed"
        return {
            "status": "completed", "verify": {"status": safe, "reason": "validation_failed" if self.exhausted else "validation_passed", "safe_validation": {"status": safe}},
            "retry": {"attempted": True, "outcome": "retry_failed" if self.exhausted else "retry_succeeded"},
            "repair": {"attempted": True, "max_attempts": 2, "attempts_used": 2 if self.exhausted else 1, "outcome": "repair_exhausted" if self.exhausted else "repair_succeeded"},
            "validation_attempts": [{"attempt_number": 1, "phase": "initial", "execution_status": "completed", "validation_status": "failed", "validation_reason": "validation_failed", "failure": {"command_id": "compile", "kind": "compile", "status": "failed", "return_code": 1, "reason_code": "failed", "stdout_tail_sha256": "a" * 64, "stderr_tail_sha256": "b" * 64}}],
        }


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

    def _evaluator_runner(self, *, task, prompt, work_root, persist_prompt):
        self.assertFalse(persist_prompt)
        run_directory = Path(work_root) / "fake"
        run_directory.mkdir(parents=True, exist_ok=True)
        stdout = run_directory / "stdout.txt"
        stdout.write_text(
            "TASK_COMPLETION_EVALUATION_JSON_BEGIN\n"
            '{"status":"completed","reason_code":"task.satisfied","satisfied_criteria":["change present"],"unsatisfied_criteria":[],"evidence_refs":["git:diff"]}'
            "\nTASK_COMPLETION_EVALUATION_JSON_END",
            encoding="utf-8",
        )
        return {"status": "completed", "stdout_path": str(stdout)}

    def _run(self, adapter):
        return run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: adapter, evaluator_runner=self._evaluator_runner)

    def test_in_memory_task_spec_override_uses_canonical_spec_hash(self):
        raw = json.loads(self.spec.read_text(encoding="utf-8"))
        spec = RepositorySingleTaskSpec(raw["schema_version"], raw["task_id"], raw["expected_head_sha"], raw["prompt"], tuple(raw["allowed_changed_paths"]), raw["commit_message"])
        result = run_repository_single_task("repo", None, task_spec_override=spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(self._modify), evaluator_runner=self._evaluator_runner, requested_run_id="run-override")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.task_spec_sha256, hashlib.sha256(serialize_repository_single_task_spec(spec).encode("utf-8")).hexdigest())

    def test_task_spec_source_requires_exactly_one_mode(self):
        raw = json.loads(self.spec.read_text(encoding="utf-8")); spec = RepositorySingleTaskSpec(raw["schema_version"], raw["task_id"], raw["expected_head_sha"], raw["prompt"], tuple(raw["allowed_changed_paths"]), raw["commit_message"])
        both = run_repository_single_task("repo", self.spec, task_spec_override=spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, requested_run_id="run-both")
        neither = run_repository_single_task("repo", None, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, requested_run_id="run-neither")
        self.assertEqual(both.reason_code, "single_task.task_spec.invalid")
        self.assertEqual(neither.reason_code, "single_task.task_spec.invalid")

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
        changed_artifact = json.loads((Path(result.receipt_path).parent / "changed_files.json").read_text(encoding="utf-8"))
        self.assertEqual(changed_artifact["actual_changed_files"], ["allowed.txt"])
        self.assertEqual(changed_artifact["commit_changed_files"], ["allowed.txt"])
        self.assertIn(("add", "--", "allowed.txt"), invocations)
        self.assertNotIn(("add", "."), invocations)
        self.assertNotIn(("add", "-A"), invocations)
        self.assertNotIn(("add", "--all"), invocations)
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(set(receipt), {"schema_version", "run_id", "status", "reason_code", "detail_reason_code", "repository_id", "task_id", "task_spec_sha256", "source_repository_root", "profile_id", "profile_base_branch", "profile_max_changed_files", "approvals", "source_state_before", "source_state_after", "expected_head_sha", "worktree_path", "worktree_preserved", "task_branch", "adapter_name", "execution_status", "validation_status", "validation_reason", "retry_attempted", "retry_outcome", "changed_files", "allowed_changed_paths", "declared_allowed_changed_paths", "actual_changed_files", "original_unexpected_changed_files", "scope_recovery_attempted", "scope_recovery_status", "auto_expanded_paths", "effective_allowed_changed_paths", "unresolved_unexpected_changed_files", "commit_created", "commit_sha", "commit_parent_sha", "commit_message", "worktree_cleanup_status", "artifact_paths", "started_at", "finished_at"})
        digest = hashlib.sha256(Path(result.receipt_path).read_bytes()).hexdigest()
        self.assertEqual(Path(result.receipt_sha256_path).read_text(encoding="utf-8"), f"{digest}  receipt.json\n")
        self.assertFalse(list(Path(result.receipt_path).parent.glob(".receipt-*.tmp")))
        self.assertNotIn("PROMPT_SECRET_MARKER_8B71", Path(result.receipt_path).read_text(encoding="utf-8"))

    def test_execution_base_uses_descendant_without_moving_source(self):
        blob = subprocess.run(["git", "-C", str(self.source), "hash-object", "-w", "--stdin"], input="previous\n", text=True, capture_output=True, check=True).stdout.strip()
        tree = subprocess.run(["git", "-C", str(self.source), "mktree"], input=f"100644 blob {blob}\tprevious.txt\n", text=True, capture_output=True, check=True).stdout.strip()
        execution_base = git(self.source, "commit-tree", tree, "-p", self.head, "-m", "Previous").stdout.strip()
        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(self._modify), evaluator_runner=self._evaluator_runner, execution_base_sha=execution_base)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.source_head_before, self.head)
        self.assertEqual(result.source_head_after, self.head)
        self.assertEqual(result.commit_parent_sha, execution_base)
        self.assertEqual(git(self.source, "rev-parse", "HEAD").stdout.strip(), self.head)
        self.assertEqual(result.changed_files, ("allowed.txt",))
        self.assertEqual(git(self.source, "show", f"{execution_base}:previous.txt").stdout, "previous\n")

    def test_invalid_execution_bases_fail_closed(self):
        for base, reason in (("z" * 40, "single_task.execution_base.invalid"), ("a" * 40, "single_task.execution_base.not_found")):
            with self.subTest(base=base):
                result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(self._modify), evaluator_runner=self._evaluator_runner, execution_base_sha=base)
                self.assertEqual(result.reason_code, reason)

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

    def test_repair_metadata_scope_artifact_and_commit_contract(self):
        adapter = RepairPreparedAdapter(self._modify)
        result = self._run(adapter)
        self.assertEqual(result.status, "completed")
        self.assertEqual(adapter.payload["allowed_changed_paths"], ("allowed.txt",))
        self.assertEqual(git(self.source, "rev-parse", f"{result.commit_sha}^").stdout.strip(), self.head)
        self.assertEqual(git(self.source, "rev-parse", "HEAD").stdout.strip(), self.head)
        self.assertEqual(git(self.source, "status", "--porcelain").stdout, "")
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        artifact = Path(receipt["artifact_paths"]["validation_attempts"])
        self.assertTrue(artifact.is_file())
        rendered = artifact.read_text(encoding="utf-8")
        self.assertNotIn("PROMPT_SECRET_MARKER_8B71", rendered)
        self.assertNotIn("PROMPT_SECRET_MARKER_8B71", Path(result.receipt_path).read_text(encoding="utf-8"))

    def test_needs_rework_runs_same_worktree_through_validation_then_evaluates_again(self):
        decisions = iter(("needs_rework", "completed"))
        roots = []
        def evaluator_runner(*, task, prompt, work_root, persist_prompt):
            roots.append(task["repo_path"])
            status = next(decisions)
            run_directory = Path(work_root) / str(len(roots))
            run_directory.mkdir(parents=True)
            output = run_directory / "stdout.txt"
            output.write_text(
                "TASK_COMPLETION_EVALUATION_JSON_BEGIN\n"
                + json.dumps({"status": status, "reason_code": "task.missing" if status == "needs_rework" else "task.done", "satisfied_criteria": [], "unsatisfied_criteria": ["required behavior"] if status == "needs_rework" else [], "evidence_refs": ["git:diff"]})
                + "\nTASK_COMPLETION_EVALUATION_JSON_END", encoding="utf-8")
            return {"status": "completed", "stdout_path": str(output)}
        adapter = FakePreparedAdapter(self._modify)
        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: adapter, evaluator_runner=evaluator_runner)
        self.assertEqual(result.status, "completed")
        self.assertEqual(adapter.calls, 2)
        self.assertEqual(len(set(roots)), 1)
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        attempts = json.loads(Path(receipt["artifact_paths"]["task_completion_attempts"]).read_text(encoding="utf-8"))["attempts"]
        self.assertEqual([item["status"] for item in attempts], ["needs_rework", "completed"])
        self.assertTrue(attempts[0]["rework_attempted"])
        changed_artifact = json.loads(Path(receipt["artifact_paths"]["changed_files"]).read_text(encoding="utf-8"))
        self.assertEqual(changed_artifact["actual_changed_files"], ["allowed.txt"])

    def test_evaluator_mutation_blocks_without_stage_or_commit(self):
        def evaluator_runner(*, task, prompt, work_root, persist_prompt):
            (Path(task["repo_path"]) / "allowed.txt").write_text("evaluator mutation\n", encoding="utf-8")
            root = Path(work_root) / "mutation"; root.mkdir(parents=True)
            output = root / "stdout.txt"
            output.write_text("TASK_COMPLETION_EVALUATION_JSON_BEGIN\n{\"status\":\"completed\",\"reason_code\":\"task.done\",\"satisfied_criteria\":[],\"unsatisfied_criteria\":[],\"evidence_refs\":[]}\nTASK_COMPLETION_EVALUATION_JSON_END", encoding="utf-8")
            return {"status": "completed", "stdout_path": str(output)}
        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(self._modify), evaluator_runner=evaluator_runner)
        self.assertEqual(result.reason_code, "single_task.task_completion.blocked")
        self.assertTrue(result.worktree_preserved)
        self.assertIsNone(result.commit_sha)
        self.assertEqual(git(self.source, "rev-list", "--count", "main").stdout.strip(), "1")

    def test_evaluator_blocked_receipt_records_final_forbidden_paths(self):
        def create_paths(worktree):
            self._modify(worktree)
            cache = worktree / "__pycache__"
            cache.mkdir()
            (cache / "forbidden.pyc").write_bytes(b"compiled")

        def evaluator_runner(*, task, prompt, work_root, persist_prompt):
            root = Path(work_root) / "blocked"; root.mkdir(parents=True)
            output = root / "stdout.txt"
            output.write_text("TASK_COMPLETION_EVALUATION_JSON_BEGIN\n{\"status\":\"blocked\",\"reason_code\":\"scope.forbidden_changed_paths\",\"satisfied_criteria\":[],\"unsatisfied_criteria\":[],\"evidence_refs\":[\"git:status\"]}\nTASK_COMPLETION_EVALUATION_JSON_END", encoding="utf-8")
            return {"status": "completed", "stdout_path": str(output)}

        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(create_paths), evaluator_runner=evaluator_runner)
        self.assertEqual(result.reason_code, "single_task.changed_files.out_of_scope")
        self.assertTrue(result.worktree_preserved)
        self.assertIsNone(result.commit_sha)
        expected = ("__pycache__/forbidden.pyc", "allowed.txt")
        self.assertEqual(result.changed_files, expected)
        artifact = json.loads((Path(result.receipt_path).parent / "changed_files.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["actual_changed_files"], list(expected))
        self.assertEqual(artifact["unexpected_changed_files"], ["__pycache__/forbidden.pyc"])
        self.assertEqual(artifact["scope_recovery_status"], "blocked")
        self.assertEqual(artifact["unresolved_unexpected_changed_files"], ["__pycache__/forbidden.pyc"])
        self.assertEqual(artifact["commit_changed_files"], [])
        actual = tuple(sorted(line[3:] for line in git(Path(result.worktree_path), "status", "--porcelain", "--untracked-files=all").stdout.splitlines()))
        self.assertEqual(actual, expected)

    def test_exhausted_repair_preserves_worktree_without_commit_and_writes_artifact(self):
        result = self._run(RepairPreparedAdapter(self._modify, exhausted=True))
        self.assertEqual(result.status, "blocked")
        self.assertTrue(result.worktree_preserved)
        self.assertTrue(Path(result.worktree_path).exists())
        self.assertEqual(git(self.source, "rev-list", "--count", "main").stdout.strip(), "1")
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        self.assertTrue(Path(receipt["artifact_paths"]["validation_attempts"]).is_file())

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

    def test_safe_support_scope_recovery_preserves_declared_scope_and_uses_effective_scope_for_evaluator(self):
        self._write_configuration(maximum=2)
        captured = {}

        def create_paths(worktree):
            self._modify(worktree)
            support = worktree / "tests" / "test_feature.py"
            support.parent.mkdir()
            support.write_text("assert True\n", encoding="utf-8")

        def evaluator_runner(*, task, prompt, work_root, persist_prompt):
            captured["prompt"] = prompt
            return self._evaluator_runner(task=task, prompt=prompt, work_root=work_root, persist_prompt=persist_prompt)

        adapter = FakePreparedAdapter(create_paths)
        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: adapter, evaluator_runner=evaluator_runner)
        self.assertEqual(result.status, "completed")
        self.assertEqual(adapter.payloads[0]["allowed_changed_paths"], ("allowed.txt",))
        self.assertIn("tests/test_feature.py", captured["prompt"])
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(receipt["declared_allowed_changed_paths"], ["allowed.txt"])
        self.assertEqual(receipt["original_unexpected_changed_files"], ["tests/test_feature.py"])
        self.assertTrue(receipt["scope_recovery_attempted"])
        self.assertEqual(receipt["scope_recovery_status"], "accepted")
        self.assertEqual(receipt["auto_expanded_paths"], ["tests/test_feature.py"])
        self.assertEqual(receipt["effective_allowed_changed_paths"], ["allowed.txt", "tests/test_feature.py"])
        self.assertEqual(receipt["unresolved_unexpected_changed_files"], [])
        self.assertEqual(git(self.source, "diff-tree", "--no-commit-id", "--name-only", "-r", result.commit_sha).stdout.splitlines(), ["allowed.txt", "tests/test_feature.py"])

    def test_unsafe_scope_recovery_blocks_before_completion_evaluator(self):
        def unexpected_source(worktree):
            self._modify(worktree)
            (worktree / "src").mkdir()
            (worktree / "src" / "unsafe.py").write_text("x\n", encoding="utf-8")

        def evaluator_runner(**_kwargs):
            self.fail("unsafe scope must block before evaluator execution")

        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(unexpected_source), evaluator_runner=evaluator_runner)
        self.assertEqual(result.reason_code, "single_task.changed_files.out_of_scope")
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(receipt["scope_recovery_status"], "blocked")
        self.assertEqual(receipt["auto_expanded_paths"], [])
        self.assertEqual(receipt["unresolved_unexpected_changed_files"], ["src/unsafe.py"])

    def test_commit_scope_still_blocks_unresolved_path_added_by_rework(self):
        calls = []

        def action(worktree):
            calls.append(worktree)
            if len(calls) == 1:
                self._modify(worktree)
            else:
                (worktree / "src").mkdir()
                (worktree / "src" / "late.py").write_text("x\n", encoding="utf-8")

        statuses = iter(("needs_rework", "completed"))
        def evaluator_runner(*, task, prompt, work_root, persist_prompt):
            status = next(statuses)
            directory = Path(work_root) / status
            directory.mkdir(parents=True, exist_ok=True)
            output = directory / "stdout.txt"
            output.write_text(
                "TASK_COMPLETION_EVALUATION_JSON_BEGIN\n"
                + json.dumps({"status": status, "reason_code": "task.more" if status == "needs_rework" else "task.done", "satisfied_criteria": [], "unsatisfied_criteria": ["more"] if status == "needs_rework" else [], "evidence_refs": []})
                + "\nTASK_COMPLETION_EVALUATION_JSON_END", encoding="utf-8",
            )
            return {"status": "completed", "stdout_path": str(output)}

        result = run_repository_single_task("repo", self.spec, registry_path=self.registry, bindings_path=self.bindings, output_root=self.output, adapter_resolver=lambda: FakePreparedAdapter(action), evaluator_runner=evaluator_runner)
        self.assertEqual(result.reason_code, "single_task.changed_files.out_of_scope")
        self.assertIsNone(result.commit_sha)
        receipt = json.loads(Path(result.receipt_path).read_text(encoding="utf-8"))
        self.assertEqual(receipt["scope_recovery_status"], "not_needed")
        self.assertEqual(receipt["unresolved_unexpected_changed_files"], ["src/late.py"])

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


    def test_production_defaults_load_home_bindings_and_persist_receipt(self):
        home = self.base / "home"
        default_bindings = (
            home
            / ".config"
            / "codex-local-runner"
            / "repository-bindings.json"
        )
        default_bindings.parent.mkdir(parents=True, exist_ok=True)
        default_bindings.write_text(
            self.bindings.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        adapter = FakePreparedAdapter(self._modify)

        with patch.dict(os.environ, {"HOME": str(home)}):
            result = run_repository_single_task(
                "repo",
                self.spec,
                registry_path=self.registry,
                adapter_resolver=lambda: adapter,
                evaluator_runner=self._evaluator_runner,
            )

        self.assertEqual(PYTHON, str(Path(sys.executable).resolve()))
        self.assertTrue(Path(PYTHON).is_file())
        self.assertEqual(result.status, "completed")
        self.assertEqual(adapter.calls, 1)

        expected_output_root = (
            home
            / ".local"
            / "state"
            / "codex-local-runner"
            / "repository-single-task-runs"
        )
        receipt_path = Path(result.receipt_path)
        self.assertTrue(receipt_path.is_relative_to(expected_output_root))
        self.assertTrue(receipt_path.is_file())

        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
        self.assertEqual(
            Path(result.receipt_sha256_path).read_text(encoding="utf-8"),
            f"{digest}  receipt.json\n",
        )
        self.assertEqual(
            git(self.source, "rev-parse", "HEAD").stdout.strip(),
            self.head,
        )
        self.assertEqual(
            git(self.source, "status", "--porcelain").stdout,
            "",
        )

    def test_unexpected_adapter_exception_is_receipt_backed_and_redacted(self):
        marker = "TOKEN_SECRET_MARKER_52AF ENV_SECRET_MARKER_91D4"

        def explode(_worktree):
            raise RuntimeError(marker)

        result = self._run(FakePreparedAdapter(explode))

        self.assertEqual(result.status, "failed")
        self.assertEqual(
            result.reason_code,
            "single_task.execution.not_completed",
        )
        self.assertTrue(result.worktree_preserved)
        self.assertTrue(Path(result.worktree_path).exists())
        self.assertTrue(Path(result.receipt_path).is_file())
        self.assertTrue(Path(result.receipt_sha256_path).is_file())

        digest = hashlib.sha256(
            Path(result.receipt_path).read_bytes()
        ).hexdigest()
        self.assertEqual(
            Path(result.receipt_sha256_path).read_text(encoding="utf-8"),
            f"{digest}  receipt.json\n",
        )

        for artifact in Path(result.receipt_path).parent.iterdir():
            if artifact.is_file():
                self.assertNotIn(
                    marker,
                    artifact.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ),
                )

        self.assertEqual(
            git(self.source, "rev-parse", "HEAD").stdout.strip(),
            self.head,
        )
        self.assertEqual(
            git(self.source, "status", "--porcelain").stdout,
            "",
        )

        branch_check = subprocess.run(
            [
                "git",
                "-C",
                str(self.source),
                "show-ref",
                "--verify",
                "--quiet",
                "refs/heads/codex-task/repo/task-1",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(branch_check.returncode, 0)


    def test_commit_uses_global_identity_from_whitelisted_environment(self):
        home = self.base / "identity-home"
        home.mkdir()
        xdg_home = home / "xdg"
        xdg_home.mkdir()

        setup_environment = os.environ.copy()
        setup_environment["HOME"] = str(home)
        setup_environment["GIT_CONFIG_GLOBAL"] = str(
            home / ".gitconfig"
        )

        subprocess.run(
            [
                "git",
                "config",
                "--global",
                "user.name",
                "Controller Global Test",
            ],
            env=setup_environment,
            text=True,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "config",
                "--global",
                "user.email",
                "controller-global@example.invalid",
            ],
            env=setup_environment,
            text=True,
            capture_output=True,
            check=True,
        )

        git(self.source, "config", "--unset-all", "user.name")
        git(self.source, "config", "--unset-all", "user.email")

        module = __import__(
            "automation.orchestration."
            "repository_resolved_single_task_controller",
            fromlist=["_git_environment"],
        )

        controlled_environment = {
            "HOME": str(home),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "XDG_CONFIG_HOME": str(xdg_home),
            "GIT_ASKPASS": "SECRET_GIT_ASKPASS",
            "SSH_ASKPASS": "SECRET_SSH_ASKPASS",
            "GH_TOKEN": "SECRET_GH_TOKEN",
            "GITHUB_TOKEN": "SECRET_GITHUB_TOKEN",
        }

        with patch.dict(
            os.environ,
            controlled_environment,
            clear=True,
        ):
            child_environment = module._git_environment()
            result = self._run(
                FakePreparedAdapter(self._modify)
            )

        self.assertEqual(
            child_environment,
            {
                "GIT_TERMINAL_PROMPT": "0",
                "LC_ALL": "C",
                "LANG": "C",
                "HOME": str(home),
                "PATH": controlled_environment["PATH"],
                "XDG_CONFIG_HOME": str(xdg_home),
            },
        )

        for forbidden in (
            "GIT_ASKPASS",
            "SSH_ASKPASS",
            "GH_TOKEN",
            "GITHUB_TOKEN",
        ):
            self.assertNotIn(forbidden, child_environment)

        self.assertEqual(result.status, "completed")
        self.assertEqual(
            result.reason_code,
            "single_task.completed",
        )
        self.assertIsNotNone(result.commit_sha)

        author = git(
            self.source,
            "show",
            "-s",
            "--format=%an%n%ae",
            result.commit_sha,
        ).stdout.splitlines()

        self.assertEqual(
            author,
            [
                "Controller Global Test",
                "controller-global@example.invalid",
            ],
        )
        self.assertEqual(
            git(
                self.source,
                "rev-parse",
                f"{result.commit_sha}^",
            ).stdout.strip(),
            self.head,
        )
        self.assertEqual(
            git(
                self.source,
                "rev-parse",
                "HEAD",
            ).stdout.strip(),
            self.head,
        )
        self.assertEqual(
            git(
                self.source,
                "status",
                "--porcelain",
            ).stdout,
            "",
        )
        self.assertFalse(Path(result.worktree_path).exists())

    def test_result_mapping_is_deterministic(self):
        result = RepositorySingleTaskRunResult("1", "run", "blocked", "single_task.changed_files.none", None, "repo", "task", "/tmp/repo", "main", "a" * 40, "a" * 40, "profile", "b" * 64, "/tmp/work", False, None, None, None, (), "codex_cli", "completed", "passed", "validation_passed", False, "not_attempted", "/tmp/r", "/tmp/s", "start", "finish")
        self.assertEqual(repository_single_task_run_result_to_mapping(result)["changed_files"], [])
        self.assertEqual(serialize_repository_single_task_run_result(result), serialize_repository_single_task_run_result(result))

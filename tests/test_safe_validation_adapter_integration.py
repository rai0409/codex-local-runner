from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.codex_cli import CodexCliAdapter
from automation.orchestration.repository_profile import APPROVAL_ACTIONS
from automation.orchestration.repository_profile import FORBIDDEN_GIT_OPERATION_IDS
from automation.orchestration.repository_profile import validate_repository_profile
from automation.orchestration.safe_validation_executor import ValidationCommandResult
from automation.orchestration.safe_validation_executor import ValidationExecutionResult
from orchestrator import main as orchestrator_main


def _profile(root: Path, *, approval: str = "automatic"):
    return validate_repository_profile({
        "schema_version": "1", "profile_id": "adapter-test", "repository_root": str(root),
        "base_branch": "main", "python_executable": sys.executable,
        "validation_commands": [{"command_id": kind, "kind": kind,
            "argv": [sys.executable, "-m", "py_compile", "x.py"], "cwd": str(root),
            "timeout_seconds": 10, "required": True, "stop_on_failure": True}
            for kind in ("focused", "related_regression", "full", "compile", "diff_check")],
        "artifact_requirements": [], "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS),
        "max_changed_files": 2,
        "approval_boundary": {action: (approval if action == "test_execution" else "automatic") for action in APPROVAL_ACTIONS},
        "environment_allowlist": [],
    })


def _safe_result(status: str) -> ValidationExecutionResult:
    result_status = "passed" if status == "passed" else "failed"
    command = ValidationCommandResult("focused", "focused", (sys.executable, "-m", "py_compile", "x.py"), "/tmp", True, True, result_status, 0 if result_status == "passed" else 1, f"safe_validation.command.{result_status}", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, "", "", False, False)
    return ValidationExecutionResult(1, "adapter-test", "/tmp", status, "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, (command,), () if status == "passed" else ("focused",), (), False, None)


class SafeValidationAdapterIntegrationTests(unittest.TestCase):
    def test_mismatch_and_nonautomatic_preflight_do_not_start_codex(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with mock.patch("adapters.codex_cli.run_codex") as codex:
                mismatch = adapter.execute({"repo_path": str(root), "work_dir": str(root), "repository_profile": _profile(root.parent)})
                denied = adapter.execute({"repo_path": str(root), "work_dir": str(root), "repository_profile": _profile(root, approval="human_required")})
        self.assertEqual(mismatch["error"], "safe_validation.profile_repository_mismatch")
        self.assertEqual(denied["error"], "safe_validation.test_execution_not_automatic")
        codex.assert_not_called()

    def test_safe_validation_is_used_for_initial_and_retry_without_legacy_runner(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            profile = _profile(root)
            execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
            with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}), mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": ""}), mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", return_value=profile), mock.patch("adapters.codex_cli.run_codex", side_effect=[execution, execution]) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=[_safe_result("failed"), _safe_result("passed")]) as validate, mock.patch("verify.runner.run_validation_commands") as legacy:
                result = adapter.execute({"repo_path": str(root), "work_dir": str(root), "repository_profile": profile, "validation_commands": ["ignored"]})
        self.assertEqual(codex.call_count, 2)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["retry"]["outcome"], "retry_succeeded")
        legacy.assert_not_called()
        self.assertNotIn("run_validation_commands", __import__("adapters.codex_cli", fromlist=["*"]).__dict__)

    def test_legacy_cli_input_is_rejected_without_command_echo(self) -> None:
        parser = orchestrator_main._build_parser()
        args = parser.parse_args(["--repo", "r", "--task-type", "t", "--goal", "g", "--validation-command", "secret command"])
        self.assertEqual(args.validation_commands, ["secret command"])

    def test_static_adapter_and_test_integrity_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        adapter_tree = ast.parse((root / "adapters/codex_cli.py").read_text(encoding="utf-8"))
        test_tree = ast.parse((root / "tests/test_execution_path.py").read_text(encoding="utf-8"))
        forbidden_calls = []
        for node in ast.walk(adapter_tree):
            if isinstance(node, ast.Call) and ((isinstance(node.func, ast.Name) and node.func.id == "run_validation_commands") or (isinstance(node.func, ast.Attribute) and node.func.attr == "run_validation_commands")):
                forbidden_calls.append(node.lineno)
            if isinstance(node, ast.ImportFrom) and node.module == "verify.runner":
                forbidden_calls.extend(alias.name for alias in node.names if alias.name == "run_validation_commands")
        self.assertEqual(forbidden_calls, [])
        replacements = []
        classes = {}
        for node in test_tree.body:
            if isinstance(node, ast.ClassDef):
                classes.setdefault(node.name, 0)
                classes[node.name] += 1
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr.startswith("test_"):
                        replacements.append(node.lineno)
        self.assertEqual(replacements, [])
        self.assertEqual(classes.get("CodexCliExecutionTests"), 1)

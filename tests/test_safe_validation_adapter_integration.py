from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from adapters.codex_cli import CodexCliAdapter
from automation.orchestration.repository_profile import APPROVAL_ACTIONS
from automation.orchestration.repository_profile import FORBIDDEN_GIT_OPERATION_IDS
from automation.orchestration.repository_profile import validate_repository_profile
from automation.orchestration.repository_profile_binding import RepositoryProfileBindingError
from automation.orchestration.safe_validation_executor import SafeValidationExecutorError
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


def _git_worktree(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "init"], check=True, capture_output=True)


def _safe_result(status: str, stdout: str = "", stderr: str = "") -> ValidationExecutionResult:
    result_status = "passed" if status == "passed" else "failed"
    command = ValidationCommandResult("focused", "focused", (sys.executable, "-m", "py_compile", "x.py"), "/tmp", True, True, result_status, 0 if result_status == "passed" else 1, f"safe_validation.command.{result_status}", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, stdout, stderr, False, False)
    return ValidationExecutionResult(1, "adapter-test", "/tmp", status, "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, (command,), () if status == "passed" else ("focused",), (), False, None)


class SafeValidationAdapterIntegrationTests(unittest.TestCase):
    def test_repair_uses_new_prompt_with_failure_context_and_scope(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); _git_worktree(root); profile = _profile(root)
            execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
            payload = {"prompt": "original task", "worktree_path": str(root), "work_dir": str(root), "repository_profile": profile, "allowed_changed_paths": ["x.py"]}
            with mock.patch("adapters.codex_cli.run_codex", side_effect=[execution, execution]) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=[_safe_result("failed", "FAILURE_OUTPUT"), _safe_result("passed")]):
                result = adapter.execute_prepared_worktree(payload)
        self.assertEqual(codex.call_count, 2)
        self.assertEqual(codex.call_args_list[0].kwargs["prompt"], "original task")
        repair_prompt = codex.call_args_list[1].kwargs["prompt"]
        self.assertTrue(all(call.kwargs["persist_prompt"] is False for call in codex.call_args_list))
        self.assertNotEqual(repair_prompt, "original task")
        self.assertIn("command_id: focused", repair_prompt); self.assertIn("FAILURE_OUTPUT", repair_prompt); self.assertIn("x.py", repair_prompt)
        self.assertEqual(result["attempt_count"], 2); self.assertEqual(result["retry"]["outcome"], "retry_succeeded")
        self.assertEqual(result["repair"], {"attempted": True, "max_attempts": 2, "attempts_used": 1, "outcome": "repair_succeeded"})
        self.assertEqual(result["verify"]["status"], "passed")
    def test_mismatch_and_nonautomatic_preflight_do_not_start_codex(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_worktree(root)
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
            _git_worktree(root)
            profile = _profile(root)
            execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
            with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}), mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": ""}), mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", return_value=profile), mock.patch("adapters.codex_cli.run_codex", side_effect=[execution, execution]) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=[_safe_result("failed"), _safe_result("passed")]) as validate, mock.patch("verify.runner.run_validation_commands") as legacy:
                result = adapter.execute({"prompt": "test prompt", "repo_path": str(root), "work_dir": str(root), "repository_profile": profile, "validation_commands": ["ignored"]})
        self.assertEqual(codex.call_count, 2)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["retry"]["outcome"], "retry_succeeded")
        legacy.assert_not_called()
        self.assertNotIn("run_validation_commands", __import__("adapters.codex_cli", fromlist=["*"]).__dict__)

    def test_executor_error_fails_closed_without_retry(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_worktree(root)
            profile = _profile(root)
            execution = {
                "status": "completed",
                "return_code": 0,
                "started_at": "a",
                "finished_at": "b",
                "artifacts": [],
                "error": "",
            }
            executor_error = SafeValidationExecutorError(
                "safe_validation.executor.internal",
                "test executor failure",
            )
            with (
                mock.patch(
                    "adapters.codex_cli.prepare_git_worktree",
                    return_value={
                        "created": True,
                        "cleanup_needed": True,
                        "worktree_path": str(root),
                        "branch_name": "branch",
                        "error": "",
                    },
                ),
                mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={"error": ""},
                ),
                mock.patch(
                    "adapters.codex_cli.bind_repository_profile_to_worktree",
                    return_value=profile,
                ),
                mock.patch(
                    "adapters.codex_cli.run_codex",
                    return_value=execution,
                ) as codex,
                mock.patch(
                    "adapters.codex_cli.execute_repository_validation",
                    side_effect=executor_error,
                ) as validate,
            ):
                result = adapter.execute(
                    {
                        "prompt": "test prompt",
                        "repo_path": str(root),
                        "work_dir": str(root),
                        "repository_profile": profile,
                    }
                )

        codex.assert_called_once()
        validate.assert_called_once()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verify"]["status"], "failed")
        self.assertFalse(result["verify"]["success"])
        self.assertEqual(
            result["verify"]["reason"],
            "safe_validation_executor_error",
        )
        self.assertFalse(result["retry"]["attempted"])
        self.assertEqual(result["retry"]["outcome"], "not_attempted")
        self.assertEqual(
            result["result_interpretation"],
            "completed_verified_failed",
        )
        self.assertEqual(
            result["review_recommendation"],
            "review_recommended",
        )
        self.assertEqual(
            result["review_handoff_summary"]["final_verify_reason"],
            "safe_validation_executor_error",
        )

    def test_executor_error_after_retry_remains_failed(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_worktree(root)
            profile = _profile(root)
            execution = {
                "status": "completed",
                "return_code": 0,
                "started_at": "a",
                "finished_at": "b",
                "artifacts": [],
                "error": "",
            }
            executor_error = SafeValidationExecutorError(
                "safe_validation.executor.internal",
                "test executor failure",
            )
            with (
                mock.patch(
                    "adapters.codex_cli.prepare_git_worktree",
                    return_value={
                        "created": True,
                        "cleanup_needed": True,
                        "worktree_path": str(root),
                        "branch_name": "branch",
                        "error": "",
                    },
                ),
                mock.patch(
                    "adapters.codex_cli.cleanup_git_worktree",
                    return_value={"error": ""},
                ),
                mock.patch(
                    "adapters.codex_cli.bind_repository_profile_to_worktree",
                    return_value=profile,
                ),
                mock.patch(
                    "adapters.codex_cli.run_codex",
                    side_effect=[execution, execution],
                ) as codex,
                mock.patch(
                    "adapters.codex_cli.execute_repository_validation",
                    side_effect=[
                        _safe_result("failed"),
                        executor_error,
                    ],
                ) as validate,
            ):
                result = adapter.execute(
                    {
                        "prompt": "test prompt",
                        "repo_path": str(root),
                        "work_dir": str(root),
                        "repository_profile": profile,
                    }
                )

        self.assertEqual(codex.call_count, 2)
        self.assertEqual(validate.call_count, 2)
        self.assertEqual(result["verify"]["status"], "failed")
        self.assertEqual(
            result["verify"]["reason"],
            "safe_validation_executor_error",
        )
        self.assertTrue(result["retry"]["attempted"])
        self.assertEqual(result["retry"]["outcome"], "retry_failed")
        self.assertEqual(
            result["result_interpretation"],
            "completed_verified_failed_after_retry",
        )
        self.assertEqual(
            result["review_recommendation"],
            "review_recommended_after_retry_failure",
        )

    def test_prepared_surface_is_canonical_and_has_no_worktree_lifecycle_calls(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            _git_worktree(root)
            profile = _profile(root)
            execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
            with mock.patch("adapters.codex_cli.run_codex", return_value=execution) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", return_value=_safe_result("passed")) as validation, mock.patch("adapters.codex_cli.prepare_git_worktree") as prepare, mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree") as bind, mock.patch("adapters.codex_cli.cleanup_git_worktree") as cleanup:
                result = adapter.execute_prepared_worktree({"prompt": "test prompt", "worktree_path": str(root), "work_dir": str(root), "repository_profile": profile})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["verify"]["reason"], "validation_passed")
        self.assertEqual(result["result_interpretation"], "completed_verified_passed")
        codex.assert_called_once(); validation.assert_called_once()
        prepare.assert_not_called(); bind.assert_not_called(); cleanup.assert_not_called()

    def test_prepared_partial_and_noncompleted_do_not_retry(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); _git_worktree(root); profile = _profile(root)
            completed = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
            failed = {"status": "failed", "return_code": 1, "started_at": "a", "finished_at": "b", "artifacts": [], "error": "failed"}
            payload = {"prompt": "test prompt", "worktree_path": str(root), "work_dir": str(root), "repository_profile": profile}
            with mock.patch("adapters.codex_cli.run_codex", return_value=completed) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", return_value=_safe_result("partial")) as validation:
                partial = adapter.execute_prepared_worktree(payload)
            self.assertEqual(codex.call_count, 1); self.assertEqual(validation.call_count, 1)
            self.assertEqual(partial["result_interpretation"], "completed_verified_partial")
            self.assertEqual(partial["retry"]["outcome"], "not_attempted")
            with mock.patch("adapters.codex_cli.run_codex", return_value=failed) as codex, mock.patch("adapters.codex_cli.execute_repository_validation") as validation:
                not_completed = adapter.execute_prepared_worktree(payload)
            self.assertEqual(codex.call_count, 1); validation.assert_not_called()
            self.assertEqual(not_completed["verify"]["reason"], "validation_not_run_execution_status_failed")

    def test_prepared_retry_failure_and_executor_errors_have_exact_outcomes(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); _git_worktree(root); profile = _profile(root)
            execution = {"status": "completed", "return_code": 0, "started_at": "a", "finished_at": "b", "artifacts": [], "error": ""}
            payload = {"prompt": "test prompt", "worktree_path": str(root), "work_dir": str(root), "repository_profile": profile}
            with mock.patch("adapters.codex_cli.run_codex", side_effect=[execution, execution, execution]) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=[_safe_result("failed"), _safe_result("failed"), _safe_result("failed")]) as validation:
                failed = adapter.execute_prepared_worktree(payload)
            self.assertEqual(codex.call_count, 3); self.assertEqual(validation.call_count, 3)
            self.assertEqual(failed["retry"]["outcome"], "retry_failed")
            self.assertEqual(failed["repair"]["attempts_used"], 2)
            self.assertEqual(failed["repair"]["outcome"], "repair_exhausted")
            self.assertEqual(failed["result_interpretation"], "completed_verified_failed_after_retry")
            error = SafeValidationExecutorError("safe_validation.executor.internal", "test executor failure")
            with mock.patch("adapters.codex_cli.run_codex", return_value=execution) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=error) as validation:
                initial_error = adapter.execute_prepared_worktree(payload)
            self.assertEqual(codex.call_count, 1); self.assertEqual(validation.call_count, 1)
            self.assertFalse(initial_error["retry"]["attempted"])
            self.assertEqual(initial_error["verify"]["reason"], "safe_validation_executor_error")
            with mock.patch("adapters.codex_cli.run_codex", side_effect=[execution, execution]) as codex, mock.patch("adapters.codex_cli.execute_repository_validation", side_effect=[_safe_result("failed"), error]) as validation:
                retry_error = adapter.execute_prepared_worktree(payload)
            self.assertEqual(codex.call_count, 2); self.assertEqual(validation.call_count, 2)
            self.assertEqual(retry_error["retry"]["outcome"], "retry_failed")
            self.assertEqual(retry_error["result_interpretation"], "completed_verified_failed_after_retry")

    def test_prepared_preflight_and_execute_delegation_are_fail_closed(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); _git_worktree(root); profile = _profile(root)
            with mock.patch("adapters.codex_cli.run_codex") as codex, mock.patch("adapters.codex_cli.execute_repository_validation") as validation:
                mismatch = adapter.execute_prepared_worktree({"prompt": "test", "worktree_path": str(root), "work_dir": str(root), "repository_profile": _profile(root.parent)})
                denied = adapter.execute_prepared_worktree({"prompt": "test", "worktree_path": str(root), "work_dir": str(root), "repository_profile": _profile(root, approval="human_required")})
            self.assertEqual(mismatch["error"], "safe_validation.profile_repository_mismatch")
            self.assertEqual(denied["error"], "safe_validation.test_execution_not_automatic")
            codex.assert_not_called(); validation.assert_not_called()
            delegated = {"adapter":"codex_cli","status":"completed","started_at":"a","finished_at":"b","artifacts":[],"error":None,"return_code":0,"verify":{"status":"passed","success":True,"commands":[],"error":"","reason":"validation_passed","safe_validation":{"status":"passed"}},"attempt_count":1,"retry":{"attempted":False,"trigger":"not_applicable","outcome":"not_attempted"},"result_interpretation":"completed_verified_passed","review_recommendation":"no_review_needed","review_handoff_summary":{},"reviewer_handoff":{}}
            with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}) as prepare, mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", return_value=profile) as bind, mock.patch.object(adapter, "execute_prepared_worktree", return_value=delegated) as prepared, mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": ""}) as cleanup:
                result = adapter.execute({"prompt": "test", "repo_path": str(root), "work_dir": str(root), "repository_profile": profile})
            self.assertIs(result, delegated)
            prepare.assert_called_once(); bind.assert_called_once(); prepared.assert_called_once(); cleanup.assert_called_once()

    def test_execute_handles_prepare_binding_and_cleanup_failures_without_execution(self) -> None:
        adapter = CodexCliAdapter()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); _git_worktree(root); profile = _profile(root)
            payload = {"prompt": "test", "repo_path": str(root), "work_dir": str(root), "repository_profile": profile}
            with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": False, "cleanup_needed": False, "worktree_path": "", "branch_name": "", "error": "prepare failed"}) as prepare, mock.patch.object(adapter, "execute_prepared_worktree") as prepared:
                preparation_failed = adapter.execute(payload)
            prepare.assert_called_once(); prepared.assert_not_called()
            self.assertEqual(preparation_failed["error"], "prepare failed")
            with mock.patch("adapters.codex_cli.prepare_git_worktree", return_value={"created": True, "cleanup_needed": True, "worktree_path": str(root), "branch_name": "branch", "error": ""}), mock.patch("adapters.codex_cli.bind_repository_profile_to_worktree", side_effect=RepositoryProfileBindingError("profile_binding.failed", "binding failed")), mock.patch.object(adapter, "execute_prepared_worktree") as prepared, mock.patch("adapters.codex_cli.cleanup_git_worktree", return_value={"error": "cleanup failed"}) as cleanup:
                binding_failed = adapter.execute(payload)
            prepared.assert_not_called(); cleanup.assert_called_once()
            self.assertIn("cleanup failed", binding_failed["error"])

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

    def test_static_execute_is_a_lifecycle_wrapper(self) -> None:
        root = Path(__file__).resolve().parents[1]
        tree = ast.parse((root / "adapters/codex_cli.py").read_text(encoding="utf-8"))
        methods = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in {"execute", "execute_prepared_worktree"}}
        def calls(method):
            return {node.func.id if isinstance(node.func, ast.Name) else node.func.attr for node in ast.walk(method) if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))}
        self.assertNotIn("run_codex", calls(methods["execute"]))
        self.assertNotIn("execute_repository_validation", calls(methods["execute"]))
        self.assertIn("execute_prepared_worktree", calls(methods["execute"]))
        self.assertIn("run_codex", calls(methods["execute_prepared_worktree"]))
        self.assertIn("execute_repository_validation", calls(methods["execute_prepared_worktree"]))

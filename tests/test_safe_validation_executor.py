from __future__ import annotations

import dataclasses
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from automation.orchestration import safe_validation_executor as module
from automation.orchestration.repository_profile import (
    APPROVAL_ACTIONS,
    FORBIDDEN_GIT_OPERATION_IDS,
    validate_repository_profile,
)
from automation.orchestration.safe_validation_executor import (
    DEFAULT_MAX_OUTPUT_BYTES,
    SAFE_VALIDATION_EXECUTOR_SCHEMA_VERSION,
    SafeValidationExecutorError,
    ValidationCommandResult,
    ValidationExecutionResult,
    execute_repository_validation,
    serialize_validation_execution_result,
    validation_execution_result_to_mapping,
)


class SafeValidationExecutorTests(unittest.TestCase):
    def profile(self, root: Path, *, commands=None, allowlist=None):
        python = str(Path(sys.executable).resolve())
        target = str(root / "test_ok.py")
        default = [
            {"command_id": command_id, "kind": kind, "argv": [python, "-m", "py_compile", target], "cwd": str(root), "timeout_seconds": 10, "required": True, "stop_on_failure": True}
            for command_id, kind in (
                ("focused", "focused"), ("related", "related_regression"), ("full", "full"),
                ("compile", "compile"), ("diff", "diff_check"),
            )
        ]
        return {
            "schema_version": "1", "profile_id": "safe-test", "repository_root": str(root),
            "base_branch": "main", "python_executable": python,
            "validation_commands": default if commands is None else commands,
            "artifact_requirements": [], "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS),
            "max_changed_files": 2,
            "approval_boundary": {action: "automatic" for action in APPROVAL_ACTIONS},
            "environment_allowlist": [] if allowlist is None else allowlist,
        }

    def error(self, callback, code):
        with self.assertRaises(SafeValidationExecutorError) as raised:
            callback()
        self.assertEqual(raised.exception.reason_code, code)

    def write_test(self, root: Path, body="def test_ok():\n    assert True\n"):
        (root / "test_ok.py").write_text(body, encoding="utf-8")

    def test_success_order_environment_popen_contract_and_frozen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            raw = self.profile(root, allowlist=["ALLOWED", "GIT_TERMINAL_PROMPT"])
            before = json.loads(json.dumps(raw))
            profile = validate_repository_profile(raw)
            original = module.subprocess.Popen
            calls = []
            def wrapped(*args, **kwargs):
                calls.append((args, kwargs))
                return original(*args, **kwargs)
            with mock.patch.object(module, "validate_repository_profile", return_value=profile), mock.patch.object(module.subprocess, "Popen", side_effect=wrapped):
                result = execute_repository_validation(profile, ambient_environment={"ALLOWED": "value", "SECRET_TOKEN": "hidden", "GIT_TERMINAL_PROMPT": "unsafe"})
            self.assertEqual(raw, before)
            self.assertEqual(result.status, "passed")
            self.assertEqual([item.command_id for item in result.command_results], ["focused", "related", "full", "compile", "diff"])
            self.assertTrue(all(item.status == "passed" for item in result.command_results))
            self.assertEqual(len(calls), 5)
            args, kwargs = calls[0]
            self.assertIsInstance(args[0], tuple)
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["cwd"], str(root.resolve()))
            self.assertIs(kwargs["stdin"], module.subprocess.DEVNULL)
            self.assertEqual(kwargs["env"]["ALLOWED"], "value")
            self.assertNotIn("SECRET_TOKEN", kwargs["env"])
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(kwargs["env"]["GIT_CONFIG_NOSYSTEM"], "1")
            self.assertNotIn("value", serialize_validation_execution_result(result))
            with self.assertRaises(dataclasses.FrozenInstanceError):
                result.status = "failed"  # type: ignore[misc]

    def test_failure_optional_partial_and_required_continue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            bad = root / "bad.py"; bad.write_text("not valid python (", encoding="utf-8")
            commands = self.profile(root)["validation_commands"]
            commands[0]["argv"][-1] = str(bad)
            commands[0]["required"] = False; commands[0]["stop_on_failure"] = False
            result = execute_repository_validation(self.profile(root, commands=commands))
            self.assertEqual(result.status, "partial")
            self.assertEqual(result.optional_failure_ids, ("focused",))
            self.assertTrue(all(item.status == "passed" for item in result.command_results[1:]))
            commands[0]["required"] = True
            result = execute_repository_validation(self.profile(root, commands=commands))
            self.assertEqual(result.status, "failed")
            self.assertEqual(result.required_failure_ids, ("focused",))
            self.assertTrue(all(item.status == "passed" for item in result.command_results[1:]))

    def test_stop_marks_later_commands_skipped_and_failure_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            bad = root / "bad.py"; bad.write_text("not valid python (", encoding="utf-8")
            commands = self.profile(root)["validation_commands"]
            commands[0]["argv"][-1] = str(bad)
            result = execute_repository_validation(self.profile(root, commands=commands))
            self.assertEqual(result.status, "failed")
            self.assertTrue(result.stopped_early)
            self.assertEqual(result.stop_reason_code, "safe_validation.command.failed")
            self.assertEqual([item.status for item in result.command_results], ["failed", "skipped", "skipped", "skipped", "skipped"])
            self.assertEqual(result.required_failure_ids, ("focused", "related", "full", "compile", "diff"))

    def test_spawn_failure_and_invalid_profile_detail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            profile = validate_repository_profile(self.profile(root))
            with mock.patch.object(module, "validate_repository_profile", return_value=profile), mock.patch.object(module.subprocess, "Popen", side_effect=OSError("unavailable")):
                result = execute_repository_validation(profile)
            self.assertEqual(result.command_results[0].status, "spawn_failed")
            self.assertEqual(result.required_failure_ids, ("focused", "related", "full", "compile", "diff"))
            invalid = self.profile(root); invalid["schema_version"] = "0"
            with self.assertRaises(SafeValidationExecutorError) as raised:
                execute_repository_validation(invalid)  # type: ignore[arg-type]
            self.assertEqual(raised.exception.reason_code, "safe_validation.profile.invalid")
            self.assertEqual(raised.exception.detail_reason_code, "profile.schema_version.unsupported")

    def test_timeout_process_cleanup_and_output_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            profile = validate_repository_profile(self.profile(root))
            timed = ValidationCommandResult("focused", "focused", profile.validation_commands[0].argv, str(root), True, True, "timed_out", -15, "safe_validation.command.timed_out", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, "", "", False, False)
            with mock.patch.object(module, "_run_command", return_value=timed):
                result = execute_repository_validation(profile, termination_grace_seconds=0.1)
            self.assertEqual(result.command_results[0].status, "timed_out")
            self.assertEqual(result.command_results[0].reason_code, "safe_validation.command.timed_out")
            self.assertTrue(result.stopped_early)
            self.assertTrue(all(item.status == "skipped" for item in result.command_results[1:]))

    def test_bounded_independent_output_invalid_utf8_and_nul(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            profile = validate_repository_profile(self.profile(root))
            captured = ValidationCommandResult("focused", "focused", profile.validation_commands[0].argv, str(root), True, False, "passed", 0, "safe_validation.command.passed", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 1.0, "A" * 64 + "\x00�", "B" * 64 + "�", True, True)
            passed = [ValidationCommandResult(item.command_id, item.kind, item.argv, item.cwd, item.required, item.stop_on_failure, "passed", 0, "safe_validation.command.passed", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:01.000000Z", 0.0, "", "", False, False) for item in profile.validation_commands[1:]]
            with mock.patch.object(module, "_run_command", side_effect=[captured, *passed]):
                result = execute_repository_validation(profile, max_output_bytes=64)
            first = result.command_results[0]
            self.assertEqual(first.status, "passed")
            self.assertTrue(first.stdout_truncated)
            self.assertTrue(first.stderr_truncated)
            self.assertLessEqual(len(first.stdout.encode("utf-8", errors="replace")), 64 * 3)
            self.assertIn("A", first.stdout)

    def test_argument_validation_and_ambient_non_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); self.write_test(root)
            profile = self.profile(root)
            ambient = {"KEEP": "v"}
            self.error(lambda: execute_repository_validation(profile, max_output_bytes=True), "safe_validation.max_output_bytes.invalid")
            self.error(lambda: execute_repository_validation(profile, termination_grace_seconds=float("nan")), "safe_validation.termination_grace_seconds.invalid")
            self.error(lambda: execute_repository_validation(profile, ambient_environment={"BAD": 1}), "safe_validation.ambient_environment.invalid")
            execute_repository_validation(profile, ambient_environment=ambient)
            self.assertEqual(ambient, {"KEEP": "v"})

    def test_mapping_serialization_and_invalid_result_contract(self):
        command = ValidationCommandResult("one", "focused", ("python",), "/tmp", True, True, "passed", 0, "safe_validation.command.passed", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:00.000000Z", 0.0, "", "", False, False)
        result = ValidationExecutionResult(SAFE_VALIDATION_EXECUTOR_SCHEMA_VERSION, "profile", "/tmp", "passed", "2026-01-01T00:00:00.000000Z", "2026-01-01T00:00:00.000000Z", 0.0, (command,), (), (), False, None)
        mapping = validation_execution_result_to_mapping(result)
        mapping["command_results"][0]["argv"].append("changed")
        self.assertEqual(command.argv, ("python",))
        serialized = serialize_validation_execution_result(result)
        self.assertEqual(serialized, serialize_validation_execution_result(result))
        self.assertEqual(json.loads(serialized)["status"], "passed")
        duplicate = dataclasses.replace(result, command_results=(command, command))
        self.error(lambda: validation_execution_result_to_mapping(duplicate), "safe_validation.result.command_id.duplicate")
        invalid = dataclasses.replace(result, status="bad")
        self.error(lambda: validation_execution_result_to_mapping(invalid), "safe_validation.result.status.invalid")
        inconsistent = dataclasses.replace(result, required_failure_ids=("one",))
        self.error(lambda: validation_execution_result_to_mapping(inconsistent), "safe_validation.result.failure_ids.inconsistent")

    def test_public_contract(self):
        self.assertEqual(module.__all__, [
            "DEFAULT_MAX_OUTPUT_BYTES", "DEFAULT_TERMINATION_GRACE_SECONDS", "MAX_OUTPUT_BYTES",
            "MAX_TERMINATION_GRACE_SECONDS", "SAFE_VALIDATION_EXECUTOR_SCHEMA_VERSION",
            "VALIDATION_COMMAND_STATUSES", "VALIDATION_EXECUTION_STATUSES",
            "SafeValidationExecutorError", "ValidationCommandResult", "ValidationExecutionResult",
            "execute_repository_validation", "serialize_validation_execution_result",
            "validation_execution_result_to_mapping",
        ])
        self.assertEqual(DEFAULT_MAX_OUTPUT_BYTES, 65536)
        self.assertEqual(module.VALIDATION_COMMAND_STATUSES, ("passed", "failed", "timed_out", "spawn_failed", "skipped"))
        self.assertEqual(module.VALIDATION_EXECUTION_STATUSES, ("passed", "partial", "failed"))
        self.assertEqual(
            [field.name for field in dataclasses.fields(ValidationCommandResult)],
            ["command_id", "kind", "argv", "cwd", "required", "stop_on_failure", "status", "return_code", "reason_code", "started_at", "finished_at", "duration_seconds", "stdout", "stderr", "stdout_truncated", "stderr_truncated"],
        )


if __name__ == "__main__":
    unittest.main()

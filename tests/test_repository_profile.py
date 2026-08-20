from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
import sys
import tempfile
import unittest

from automation.orchestration import repository_profile as module
from automation.orchestration.repository_profile import (
    APPROVAL_ACTIONS, APPROVAL_MODES, ARTIFACT_EXPECTED_TYPES,
    FORBIDDEN_GIT_OPERATION_IDS, VALIDATION_COMMAND_KINDS, ApprovalBoundary,
    RepositoryProfile, RepositoryProfileValidationError, ValidationCommand,
    load_repository_profile, repository_profile_to_mapping,
    serialize_repository_profile, validate_repository_profile,
)


class RepositoryProfileTests(unittest.TestCase):
    def payload(self, root: str, **changes):
        python = str(Path(sys.executable).resolve())
        commands = [
            {"command_id": "focused", "kind": "focused", "argv": [python, "-m", "pytest", "tests/test_repository_profile.py", "-q"], "cwd": ".", "timeout_seconds": 60, "required": True, "stop_on_failure": True},
            {"command_id": "related", "kind": "related_regression", "argv": [python, "-m", "pytest", "tests/test_repository_state_analyzer.py", "-q"], "cwd": ".", "timeout_seconds": 60, "required": True, "stop_on_failure": True},
            {"command_id": "full", "kind": "full", "argv": [python, "-m", "pytest", "-q"], "cwd": ".", "timeout_seconds": 120, "required": True, "stop_on_failure": True},
            {"command_id": "compile", "kind": "compile", "argv": [python, "-m", "py_compile", "module.py"], "cwd": ".", "timeout_seconds": 30, "required": True, "stop_on_failure": True},
            {"command_id": "diff", "kind": "diff_check", "argv": ["git", "diff", "--check"], "cwd": ".", "timeout_seconds": 30, "required": True, "stop_on_failure": True},
        ]
        value = {
            "schema_version": "1", "profile_id": "sample", "repository_root": root,
            "base_branch": "main", "python_executable": python,
            "validation_commands": commands, "artifact_requirements": [],
            "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS),
            "max_changed_files": 2,
            "approval_boundary": {action: ("automatic" if action in {"code_changes", "test_execution", "artifact_generation"} else "human_required" if action not in {"tag", "release"} else "forbidden") for action in APPROVAL_ACTIONS},
            "environment_allowlist": ["PATH", "LC_ALL"],
        }
        value.update(changes)
        return value

    def error(self, payload, code: str):
        with self.assertRaises(RepositoryProfileValidationError) as raised:
            validate_repository_profile(payload)
        self.assertEqual(raised.exception.reason_code, code)

    def test_valid_contract_normalizes_paths_orders_and_is_frozen(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory); (root / "nested").mkdir()
            raw = self.payload(str(root), repository_root=str(root / "."), python_executable=sys.executable,
                artifact_requirements=[
                    {"artifact_id": "z", "path": "future/z.json", "required": True, "expected_type": "json", "minimum_size_bytes": 1, "parse_json": True, "required_keys": ["z", "a"], "readback_required": True, "checksum_required": True, "allow_outside_repository": False},
                    {"artifact_id": "a", "path": str(Path(outside) / "receipt"), "required": False, "expected_type": "text", "minimum_size_bytes": 0, "parse_json": False, "required_keys": [], "readback_required": False, "checksum_required": False, "allow_outside_repository": True},
                ], environment_allowlist=["PATH", "LC_ALL"])
            before = copy.deepcopy(raw)
            profile = validate_repository_profile(raw)
        self.assertEqual(profile.repository_root, str(root.resolve()))
        self.assertEqual(tuple(item.kind for item in profile.validation_commands), VALIDATION_COMMAND_KINDS)
        self.assertEqual(tuple(item.artifact_id for item in profile.artifact_requirements), ("a", "z"))
        self.assertEqual(profile.environment_allowlist, ("LC_ALL", "PATH"))
        self.assertEqual(raw, before)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            profile.base_branch = "other"  # type: ignore[misc]
        self.assertTrue(all(isinstance(item.argv, tuple) for item in profile.validation_commands))

    def test_strict_schema_and_types(self):
        with tempfile.TemporaryDirectory() as root:
            missing = self.payload(root); missing.pop("profile_id")
            self.error(missing, "profile.profile_id.required")
            self.error(self.payload(root, unknown=True), "profile.unknown.unknown_field")
            bad_command = self.payload(root); bad_command["validation_commands"][0]["unknown"] = True
            self.error(bad_command, "profile.validation_commands[0].unknown.unknown_field")
            bad_artifact = self.payload(root, artifact_requirements=[{"artifact_id": "a"}])
            self.error(bad_artifact, "profile.artifact_requirements[0].allow_outside_repository.required")
            bad_boundary = self.payload(root); bad_boundary["approval_boundary"]["unknown"] = "automatic"
            self.error(bad_boundary, "profile.approval_boundary.unknown.unknown_field")
            self.error(self.payload(root, schema_version="2"), "profile.schema_version.unsupported")
            timeout = self.payload(root); timeout["validation_commands"][0]["timeout_seconds"] = True
            self.error(timeout, "profile.validation_commands[0].timeout_seconds.invalid_type")
            self.error(self.payload(root, max_changed_files=True), "profile.max_changed_files.invalid_type")
            self.assertEqual(validate_repository_profile(self.payload(root, execution_timeout_seconds=1200)).execution_timeout_seconds, 1200)
            for invalid in (True, "900", 0, -1):
                self.error(self.payload(root, execution_timeout_seconds=invalid), "profile.execution_timeout_seconds.invalid_type")
            self.error(self.payload(root, execution_timeout_seconds=1801), "profile.execution_timeout_seconds.invalid_value")

    def test_command_uniqueness_kinds_and_argv_safety(self):
        with tempfile.TemporaryDirectory() as root:
            duplicate = self.payload(root); duplicate["validation_commands"][1]["command_id"] = "focused"
            self.error(duplicate, "profile.validation_commands[1].command_id.duplicate")
            duplicate_kind = self.payload(root); duplicate_kind["validation_commands"][1]["kind"] = "focused"
            self.error(duplicate_kind, "profile.validation_commands[1].kind.duplicate")
            missing = self.payload(root); missing["validation_commands"] = missing["validation_commands"][:-1]
            self.error(missing, "profile.validation_commands.missing_kind")
            string = self.payload(root); string["validation_commands"][0]["argv"] = "python -m pytest"
            self.error(string, "profile.validation_commands[0].argv.invalid_type")
            empty = self.payload(root); empty["validation_commands"][0]["argv"] = []
            self.error(empty, "profile.validation_commands[0].argv.empty")
            inline = self.payload(root); inline["validation_commands"][0]["argv"] = [sys.executable, "-c", "x=1"]
            self.error(inline, "profile.validation_commands[0].python_operation_forbidden")
            dash = self.payload(root); dash["validation_commands"][0]["argv"] = [sys.executable, "-"]
            self.error(dash, "profile.validation_commands[0].python_operation_forbidden")
            arbitrary = self.payload(root); arbitrary["validation_commands"][0]["argv"] = ["/bin/rm", "x"]
            self.error(arbitrary, "profile.validation_commands[0].executable.not_allowed")

    def test_git_parsing_allows_read_only_and_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as root:
            profile = self.payload(root)
            profile["validation_commands"][4]["argv"] = ["git", "-C", root, "diff", "--", "reset"]
            self.assertEqual(validate_repository_profile(profile).validation_commands[-1].argv[1], "-C")
            for argv in (["git", "reset", "--hard"], ["git", "-C", root, "reset", "--hard"], ["git", "push", "--force"]):
                bad = self.payload(root); bad["validation_commands"][4]["argv"] = argv
                self.error(bad, "profile.validation_commands[4].git_operation_forbidden")
            branch = self.payload(root); branch["validation_commands"][4]["argv"] = ["git", "branch", "--show-current"]
            validate_repository_profile(branch)

    def test_paths_and_artifact_consistency(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            out = Path(outside)
            cwd = self.payload(root); cwd["validation_commands"][0]["cwd"] = outside
            self.error(cwd, "profile.validation_commands[0].cwd.outside_repository")
            absent = self.payload(root); absent["validation_commands"][0]["cwd"] = "missing"
            self.error(absent, "profile.validation_commands[0].cwd.not_found")
            file = Path(root, "file"); file.write_text("x", encoding="utf-8")
            file_cwd = self.payload(root); file_cwd["validation_commands"][0]["cwd"] = str(file)
            self.error(file_cwd, "profile.validation_commands[0].cwd.not_directory")
            artifact = {"artifact_id": "a", "path": str(out / "x"), "required": True, "expected_type": "json", "minimum_size_bytes": 0, "parse_json": True, "required_keys": [], "readback_required": True, "checksum_required": False, "allow_outside_repository": False}
            self.error(self.payload(root, artifact_requirements=[artifact]), "profile.artifact_requirements[0].path.outside_repository")
            artifact["allow_outside_repository"] = True
            validate_repository_profile(self.payload(root, artifact_requirements=[artifact]))
            artifact.update({"expected_type": "directory", "minimum_size_bytes": 1, "parse_json": False})
            self.error(self.payload(root, artifact_requirements=[artifact]), "profile.artifact_requirements[0].minimum_size_bytes.inconsistent")

    def test_symlink_escape_base_branch_and_python_path_validation(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            link = Path(root, "escape")
            link.symlink_to(outside, target_is_directory=True)
            cwd = self.payload(root); cwd["validation_commands"][0]["cwd"] = "escape"
            self.error(cwd, "profile.validation_commands[0].cwd.outside_repository")
            artifact = {"artifact_id": "escape", "path": "escape/future.json", "required": False, "expected_type": "json", "minimum_size_bytes": 0, "parse_json": False, "required_keys": [], "readback_required": False, "checksum_required": False, "allow_outside_repository": False}
            self.error(self.payload(root, artifact_requirements=[artifact]), "profile.artifact_requirements[0].path.symlink_escape")
            for branch in ("bad branch", "bad..branch", "bad@{x", "bad.lock"):
                self.error(self.payload(root, base_branch=branch), "profile.base_branch.invalid_value")
            self.error(self.payload(root, python_executable="missing-python"), "profile.python_executable.not_found")
            directory = self.payload(root, python_executable=root)
            self.error(directory, "profile.python_executable.not_file")

    def test_python_symlink_path_is_preserved_for_validation_commands(self):
        with tempfile.TemporaryDirectory() as root:
            python_link = Path(root, "venv-python")
            try:
                python_link.symlink_to(Path(sys.executable).resolve())
            except OSError as exc:
                self.skipTest(f"symlink unavailable: {exc}")

            profile = validate_repository_profile(
                self.payload(
                    root,
                    python_executable=str(python_link),
                )
            )

            self.assertEqual(
                profile.python_executable,
                str(python_link),
            )

            for command in profile.validation_commands:
                if command.kind != "diff_check":
                    self.assertEqual(
                        command.argv[0],
                        str(python_link),
                    )

    def test_directly_constructed_invalid_nested_instances_are_revalidated(self):
        with tempfile.TemporaryDirectory() as root:
            profile = validate_repository_profile(self.payload(root))
            command = ValidationCommand("focused", "focused", (profile.python_executable, "-c", "x"), profile.repository_root, 1, True, True)
            invalid = RepositoryProfile(profile.schema_version, profile.profile_id, profile.repository_root, profile.base_branch, profile.python_executable, (command, *profile.validation_commands[1:]), profile.artifact_requirements, profile.forbidden_git_operations, profile.max_changed_files, profile.approval_boundary, profile.environment_allowlist)
            self.error(invalid, "profile.validation_commands[0].python_operation_forbidden")
            boundary = ApprovalBoundary(*(["invalid"] * len(APPROVAL_ACTIONS)))
            invalid_boundary = RepositoryProfile(profile.schema_version, profile.profile_id, profile.repository_root, profile.base_branch, profile.python_executable, profile.validation_commands, profile.artifact_requirements, profile.forbidden_git_operations, profile.max_changed_files, boundary, profile.environment_allowlist)
            self.error(invalid_boundary, "profile.approval_boundary.code_changes.invalid_value")

    def test_artifact_duplicate_environment_forbidden_and_approval(self):
        with tempfile.TemporaryDirectory() as root:
            item = {"artifact_id": "a", "path": "a", "required": False, "expected_type": "json", "minimum_size_bytes": 0, "parse_json": True, "required_keys": ["x", "x"], "readback_required": True, "checksum_required": False, "allow_outside_repository": False}
            self.error(self.payload(root, artifact_requirements=[item]), "profile.artifact_requirements[0].required_keys.duplicate")
            forbid = self.payload(root); forbid["forbidden_git_operations"].append(FORBIDDEN_GIT_OPERATION_IDS[0])
            self.error(forbid, "profile.forbidden_git_operations[11].duplicate")
            self.error(self.payload(root, forbidden_git_operations=[]), "profile.forbidden_git_operations.missing_required")
            env = self.payload(root, environment_allowlist=["A=A"])
            self.error(env, "profile.environment_allowlist[0].invalid_value")
            boundary = self.payload(root); boundary["approval_boundary"]["push"] = "bad"
            self.error(boundary, "profile.approval_boundary.push.invalid_value")
            for mode in APPROVAL_MODES:
                raw = self.payload(root); raw["approval_boundary"] = {action: mode for action in APPROVAL_ACTIONS}
                validate_repository_profile(raw)

    def test_instance_revalidation_mapping_serialization_and_exports(self):
        with tempfile.TemporaryDirectory() as root:
            profile = validate_repository_profile(self.payload(root))
            self.assertEqual(validate_repository_profile(profile), profile)
            invalid = RepositoryProfile("0", profile.profile_id, profile.repository_root, profile.base_branch, profile.python_executable, profile.validation_commands, profile.artifact_requirements, profile.forbidden_git_operations, profile.max_changed_files, profile.approval_boundary, profile.environment_allowlist)
            self.error(invalid, "profile.schema_version.unsupported")
            mapping = repository_profile_to_mapping(profile)
            mapping["validation_commands"][0]["argv"].append("changed")
            self.assertNotIn("changed", profile.validation_commands[0].argv)
            self.assertEqual(serialize_repository_profile(profile), serialize_repository_profile(profile))
            self.assertEqual(json.loads(serialize_repository_profile(profile)), repository_profile_to_mapping(profile))
            self.assertEqual(module.__all__, ["APPROVAL_ACTIONS", "APPROVAL_MODES", "ARTIFACT_EXPECTED_TYPES", "FORBIDDEN_GIT_OPERATION_IDS", "REPOSITORY_PROFILE_SCHEMA_VERSION", "VALIDATION_COMMAND_KINDS", "ApprovalBoundary", "ArtifactRequirement", "RepositoryProfile", "RepositoryProfileValidationError", "ValidationCommand", "load_repository_profile", "repository_profile_to_mapping", "serialize_repository_profile", "validate_repository_profile"])
            self.assertEqual([field.name for field in dataclasses.fields(ValidationCommand)], ["command_id", "kind", "argv", "cwd", "timeout_seconds", "required", "stop_on_failure"])

    def test_loader_and_root_errors(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root, "profile.json")
            path.write_text(json.dumps(self.payload(root)), encoding="utf-8")
            self.assertEqual(load_repository_profile(path).profile_id, "sample")
            self.error(self.payload("relative"), "profile.repository_root.not_absolute")
            with self.assertRaises(RepositoryProfileValidationError) as raised:
                load_repository_profile(True)  # type: ignore[arg-type]
            self.assertEqual(raised.exception.reason_code, "profile_file.invalid_type")
            with self.assertRaises(RepositoryProfileValidationError) as raised:
                load_repository_profile(Path(root, "missing.json"))
            self.assertEqual(raised.exception.reason_code, "profile_file.not_found")
            with self.assertRaises(RepositoryProfileValidationError) as raised:
                load_repository_profile(root)
            self.assertEqual(raised.exception.reason_code, "profile_file.not_file")
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(RepositoryProfileValidationError) as raised:
                load_repository_profile(path)
            self.assertEqual(raised.exception.reason_code, "profile_file.root.invalid_type")
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(RepositoryProfileValidationError) as raised:
                load_repository_profile(path)
            self.assertEqual(raised.exception.reason_code, "profile_file.json_invalid")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import dataclasses
import json
from pathlib import Path
import sys
import tempfile
import unittest

from automation.orchestration import repository_registry as module
from automation.orchestration.repository_profile import (
    APPROVAL_ACTIONS,
    FORBIDDEN_GIT_OPERATION_IDS,
)
from automation.orchestration.repository_registry import (
    DEFAULT_REPOSITORY_BINDINGS_PATH,
    REPOSITORY_BINDINGS_SCHEMA_VERSION,
    REPOSITORY_REGISTRY_SCHEMA_VERSION,
    REPOSITORY_RESOLUTION_STATUSES,
    RepositoryBinding,
    RepositoryDeclaration,
    RepositoryRegistry,
    RepositoryRegistryValidationError,
    load_repository_bindings,
    load_repository_registry,
    repository_registry_to_mapping,
    resolve_repository,
    serialize_repository_registry,
    validate_repository_bindings,
    validate_repository_registry,
)


class RepositoryRegistryTests(unittest.TestCase):
    def source(self, repos=None):
        return {
            "version": 1,
            "repos": repos
            if repos is not None
            else [
                {"name": "second", "logical_role": "managed repository"},
                {"name": "first", "logical_role": "managed repository"},
            ],
        }

    def profile(self, root: str, profile_id: str):
        python = str(Path(sys.executable).resolve())
        commands = [
            {"command_id": "focused", "kind": "focused", "argv": [python, "-m", "pytest", "-q"], "cwd": ".", "timeout_seconds": 1, "required": True, "stop_on_failure": True},
            {"command_id": "related", "kind": "related_regression", "argv": [python, "-m", "pytest", "-q"], "cwd": ".", "timeout_seconds": 1, "required": True, "stop_on_failure": True},
            {"command_id": "full", "kind": "full", "argv": [python, "-m", "pytest", "-q"], "cwd": ".", "timeout_seconds": 1, "required": True, "stop_on_failure": True},
            {"command_id": "compile", "kind": "compile", "argv": [python, "-m", "py_compile", "x.py"], "cwd": ".", "timeout_seconds": 1, "required": True, "stop_on_failure": True},
            {"command_id": "diff", "kind": "diff_check", "argv": ["git", "diff", "--check"], "cwd": ".", "timeout_seconds": 1, "required": True, "stop_on_failure": True},
        ]
        return {
            "schema_version": "1", "profile_id": profile_id,
            "repository_root": root, "base_branch": "main",
            "python_executable": python, "validation_commands": commands,
            "artifact_requirements": [],
            "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS),
            "max_changed_files": 2,
            "approval_boundary": {
                action: "automatic" if action in {"code_changes", "test_execution", "artifact_generation"}
                else "forbidden" if action in {"tag", "release"} else "human_required"
                for action in APPROVAL_ACTIONS
            },
            "environment_allowlist": [],
        }

    def bindings(self, entries):
        return {"version": 1, "bindings": entries}

    def error(self, callback, code):
        with self.assertRaises(RepositoryRegistryValidationError) as raised:
            callback()
        self.assertEqual(raised.exception.reason_code, code)

    def test_legacy_source_defaults_normalization_and_frozen_models(self):
        raw = self.source()
        before = copy.deepcopy(raw)
        registry = validate_repository_registry(raw)
        self.assertEqual(raw, before)
        self.assertEqual([item.name for item in registry.declarations], ["first", "second"])
        self.assertTrue(all(item.enabled for item in registry.declarations))
        self.assertEqual([item.profile_id for item in registry.declarations], ["first", "second"])
        self.assertEqual(registry.bindings, ())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            registry.version = 2  # type: ignore[misc]
        self.assertTrue(all(isinstance(item, tuple) for item in (registry.declarations, registry.bindings)))

    def test_legacy_actual_config_is_compatible_and_unbound(self):
        registry = load_repository_registry("config/repos.yaml")
        self.assertEqual(registry.version, 1)
        self.assertEqual(len(registry.declarations), 9)
        self.assertEqual(registry.declarations[0].name, "Jstocks-prediction")
        self.assertEqual(
            {item.status for item in module.list_repository_resolutions(registry)}, {"unbound"}
        )

    def test_source_schema_reason_codes_and_duplicate_profile_id(self):
        self.error(lambda: validate_repository_registry([]), "registry.invalid_type")
        self.error(lambda: validate_repository_registry({"repos": []}), "registry.version.required")
        self.error(lambda: validate_repository_registry({"version": True, "repos": []}), "registry.version.invalid_type")
        self.error(lambda: validate_repository_registry({"version": 2, "repos": []}), "registry.version.unsupported")
        self.error(lambda: validate_repository_registry({"version": 1, "repos": "x"}), "registry.repos.invalid_type")
        self.error(lambda: validate_repository_registry({"version": 1, "repos": []}), "registry.repos.empty")
        self.error(lambda: validate_repository_registry(self.source([{"name": "bad/name", "logical_role": "role"}])), "registry.repos[0].name.invalid_value")
        self.error(lambda: validate_repository_registry(self.source([{"name": "one", "logical_role": "role", "root": "/tmp"}])), "registry.repos[0].root.unknown_field")
        self.error(lambda: validate_repository_registry(self.source([{"name": "one", "logical_role": "role"}, {"name": "one", "logical_role": "other"}])), "registry.repos[1].name.duplicate")
        self.error(lambda: validate_repository_registry(self.source([{"name": "one", "logical_role": "role", "profile_id": "same"}, {"name": "two", "logical_role": "role", "profile_id": "same"}])), "registry.repos[1].profile_id.duplicate")

    def test_bindings_schema_paths_instances_and_loader(self):
        declarations = validate_repository_registry(self.source()).declarations
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binding_file = root / "nested" / "bindings.json"
            binding_file.parent.mkdir()
            raw = self.bindings([
                {"repository_id": "second", "profile_path": "../profile-two.json"},
                {"repository_id": "first", "profile_path": str(root / "profile-one.json")},
            ])
            bindings = validate_repository_bindings(raw, declarations, base_directory=binding_file.parent)
            self.assertEqual([item.repository_id for item in bindings], ["first", "second"])
            self.assertTrue(all(Path(item.profile_path).is_absolute() for item in bindings))
            binding_file.write_text(json.dumps(raw), encoding="utf-8")
            loaded = load_repository_bindings(binding_file, declarations)
            self.assertEqual(loaded, bindings)
            self.assertEqual(
                validate_repository_bindings(list(bindings), list(declarations), base_directory=root),
                bindings,
            )

    def test_binding_errors_and_bundle_contract(self):
        declarations = validate_repository_registry(self.source()).declarations
        self.error(
            lambda: validate_repository_bindings({"version": 1, "bindings": "x"}, declarations),
            "bindings.bindings.invalid_type",
        )
        self.error(lambda: validate_repository_bindings({"bindings": []}, declarations), "bindings.version.required")
        self.error(lambda: validate_repository_bindings(self.bindings([{"repository_id": "first", "profile_path": "x"}]), declarations), "bindings.bindings[0].profile_path.relative_without_base")
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            self.error(lambda: validate_repository_bindings(self.bindings([{"repository_id": "unknown", "profile_path": "x"}]), declarations, base_directory=base), "bindings.bindings[0].repository_id.unknown")
            self.error(lambda: validate_repository_bindings(self.bindings([{"repository_id": "first", "profile_path": "x"}, {"repository_id": "first", "profile_path": "y"}]), declarations, base_directory=base), "bindings.bindings[1].repository_id.duplicate")
            self.error(lambda: validate_repository_bindings(self.bindings([]), declarations, base_directory=base / "missing"), "bindings.base_directory.not_found")
        self.error(lambda: validate_repository_registry({"registry": self.source(), "bindings": self.bindings([])}, self.bindings([])), "registry_bundle.bindings_argument.conflict")
        self.error(lambda: validate_repository_registry({"registry": self.source(), "bindings": self.bindings([]), "extra": True}), "registry_bundle.extra.unknown_field")

    def test_resolution_states_profile_details_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = self.source([
                {"name": "ok", "logical_role": "role"},
                {"name": "disabled", "logical_role": "role", "enabled": False},
                {"name": "missing", "logical_role": "role"},
                {"name": "invalid", "logical_role": "role"},
                {"name": "mismatch", "logical_role": "role"},
            ])
            profile_path = base / "ok.json"
            profile_path.write_text(json.dumps(self.profile(str(base), "ok")), encoding="utf-8")
            invalid_path = base / "invalid.json"; invalid_path.write_text("{", encoding="utf-8")
            mismatch_path = base / "mismatch.json"; mismatch_path.write_text(json.dumps(self.profile(str(base), "different")), encoding="utf-8")
            registry = validate_repository_registry(source, self.bindings([
                {"repository_id": "ok", "profile_path": str(profile_path)},
                {"repository_id": "disabled", "profile_path": str(base / "missing-disabled.json")},
                {"repository_id": "missing", "profile_path": str(base / "missing.json")},
                {"repository_id": "invalid", "profile_path": str(invalid_path)},
                {"repository_id": "mismatch", "profile_path": str(mismatch_path)},
            ]))
            statuses = {item.repository_id: item for item in module.list_repository_resolutions(registry)}
            self.assertEqual(statuses["ok"].status, "resolved")
            self.assertEqual(statuses["disabled"].status, "disabled")
            self.assertEqual(statuses["missing"].detail_reason_code, "profile_file.not_found")
            self.assertEqual(statuses["invalid"].detail_reason_code, "profile_file.json_invalid")
            self.assertEqual(statuses["mismatch"].status, "profile_id_mismatch")
            self.assertEqual(resolve_repository(registry, "ok").profile.profile_id, "ok")
            self.error(lambda: resolve_repository(registry, "disabled"), "registry.resolution[disabled].disabled")
            self.error(lambda: resolve_repository(registry, "missing"), "registry.resolution[missing].profile_missing")
            self.error(lambda: resolve_repository(registry, "unknown"), "registry.resolution[unknown].repository_unknown")

    def test_duplicate_roots_and_symlink_equivalence(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            link = base / "link"; link.symlink_to(base, target_is_directory=True)
            first = base / "first.json"; second = base / "second.json"
            first.write_text(json.dumps(self.profile(str(base), "first")), encoding="utf-8")
            second.write_text(json.dumps(self.profile(str(link), "second")), encoding="utf-8")
            registry = validate_repository_registry(
                self.source(),
                self.bindings([
                    {"repository_id": "first", "profile_path": str(first)},
                    {"repository_id": "second", "profile_path": str(second)},
                ]),
            )
            resolutions = module.list_repository_resolutions(registry)
            self.assertEqual([item.status for item in resolutions], ["duplicate_repository_root", "duplicate_repository_root"])
            self.assertTrue(all(item.resolved_repository is None for item in resolutions))

    def test_instance_revalidation_mapping_serialization_and_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            raw = self.source()
            registry = validate_repository_registry(raw)
            invalid = RepositoryRegistry(0, registry.declarations, registry.bindings)
            self.error(lambda: validate_repository_registry(invalid), "registry.version.unsupported")
            bad_binding = RepositoryBinding("first", "relative.json")
            self.error(lambda: validate_repository_registry(RepositoryRegistry(1, registry.declarations, (bad_binding,))), "bindings.bindings[0].profile_path.relative_without_base")
            mapping = repository_registry_to_mapping(registry)
            mapping["registry"]["repos"][0]["name"] = "changed"
            self.assertNotEqual(registry.declarations[0].name, "changed")
            first = validate_repository_registry(self.source(), self.bindings([]))
            second = validate_repository_registry(
                self.source(list(reversed(self.source()["repos"]))), self.bindings([])
            )
            self.assertEqual(repository_registry_to_mapping(first), repository_registry_to_mapping(second))
            self.assertEqual(serialize_repository_registry(first), serialize_repository_registry(second))
            self.assertEqual(validate_repository_registry(json.loads(serialize_repository_registry(first))), first)
        self.assertEqual(DEFAULT_REPOSITORY_BINDINGS_PATH, "~/.config/codex-local-runner/repository-bindings.json")
        self.assertEqual(REPOSITORY_REGISTRY_SCHEMA_VERSION, 1)
        self.assertEqual(REPOSITORY_BINDINGS_SCHEMA_VERSION, 1)
        self.assertEqual(REPOSITORY_RESOLUTION_STATUSES[0], "resolved")
        self.assertEqual(module.__all__, [
            "DEFAULT_REPOSITORY_BINDINGS_PATH", "REPOSITORY_BINDINGS_SCHEMA_VERSION",
            "REPOSITORY_REGISTRY_SCHEMA_VERSION", "REPOSITORY_RESOLUTION_STATUSES",
            "RepositoryBinding", "RepositoryDeclaration", "RepositoryRegistry",
            "RepositoryRegistryValidationError", "RepositoryResolution",
            "ResolvedRepository", "list_repository_resolutions",
            "load_repository_bindings", "load_repository_registry",
            "repository_registry_to_mapping", "resolve_repository",
            "serialize_repository_registry", "validate_repository_bindings",
            "validate_repository_registry",
        ])
        self.assertEqual([field.name for field in dataclasses.fields(RepositoryDeclaration)], ["name", "logical_role", "enabled", "profile_id", "description"])
        self.assertEqual([field.name for field in dataclasses.fields(RepositoryBinding)], ["repository_id", "profile_path"])

    def test_loaders_and_file_errors(self):
        declarations = validate_repository_registry(self.source()).declarations
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.error(lambda: load_repository_bindings(root / "missing.json", declarations), "bindings_file.not_found")
            self.error(lambda: load_repository_bindings(root, declarations), "bindings_file.not_file")
            invalid = root / "invalid.json"; invalid.write_text("{", encoding="utf-8")
            self.error(lambda: load_repository_bindings(invalid, declarations), "bindings_file.json_invalid")
            array = root / "array.json"; array.write_text("[]", encoding="utf-8")
            self.error(lambda: load_repository_bindings(array, declarations), "bindings_file.root.invalid_type")
            self.error(lambda: load_repository_registry(root / "missing.yaml"), "registry_file.not_found")
            self.error(lambda: load_repository_registry(root), "registry_file.not_file")


if __name__ == "__main__":
    unittest.main()

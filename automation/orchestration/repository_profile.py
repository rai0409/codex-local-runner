"""Strict, read-only repository runtime profile contracts.

This module validates declarations only.  It never executes profile commands and
does not grant execution authorization.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Mapping

REPOSITORY_PROFILE_SCHEMA_VERSION = "1"
VALIDATION_COMMAND_KINDS = ("focused", "related_regression", "full", "compile", "diff_check")
ARTIFACT_EXPECTED_TYPES = ("file", "text", "json", "directory")
APPROVAL_MODES = ("automatic", "human_required", "forbidden")
APPROVAL_ACTIONS = (
    "code_changes", "test_execution", "artifact_generation", "stage", "commit",
    "push", "pull_request", "merge", "tag", "release",
)
FORBIDDEN_GIT_OPERATION_IDS = (
    "reset_hard", "clean_force", "force_push", "direct_base_commit", "direct_base_push",
    "branch_delete", "remote_branch_delete", "tag_mutation", "history_rewrite",
    "worktree_overwrite", "git_config_write",
)

_ROOT_FIELDS = frozenset(("schema_version", "profile_id", "repository_root", "base_branch", "python_executable", "validation_commands", "artifact_requirements", "forbidden_git_operations", "max_changed_files", "approval_boundary", "environment_allowlist"))
_COMMAND_FIELDS = frozenset(("command_id", "kind", "argv", "cwd", "timeout_seconds", "required", "stop_on_failure"))
_ARTIFACT_FIELDS = frozenset(("artifact_id", "path", "required", "expected_type", "minimum_size_bytes", "parse_json", "required_keys", "readback_required", "checksum_required", "allow_outside_repository"))
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class RepositoryProfileValidationError(ValueError):
    """Validation failure carrying a stable machine-readable reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class ValidationCommand:
    command_id: str
    kind: str
    argv: tuple[str, ...]
    cwd: str
    timeout_seconds: int
    required: bool
    stop_on_failure: bool


@dataclass(frozen=True)
class ArtifactRequirement:
    artifact_id: str
    path: str
    required: bool
    expected_type: str
    minimum_size_bytes: int
    parse_json: bool
    required_keys: tuple[str, ...]
    readback_required: bool
    checksum_required: bool
    allow_outside_repository: bool


@dataclass(frozen=True)
class ApprovalBoundary:
    code_changes: str
    test_execution: str
    artifact_generation: str
    stage: str
    commit: str
    push: str
    pull_request: str
    merge: str
    tag: str
    release: str


@dataclass(frozen=True)
class RepositoryProfile:
    schema_version: str
    profile_id: str
    repository_root: str
    base_branch: str
    python_executable: str
    validation_commands: tuple[ValidationCommand, ...]
    artifact_requirements: tuple[ArtifactRequirement, ...]
    forbidden_git_operations: tuple[str, ...]
    max_changed_files: int
    approval_boundary: ApprovalBoundary
    environment_allowlist: tuple[str, ...]


def _error(code: str, message: str) -> RepositoryProfileValidationError:
    return RepositoryProfileValidationError(code, message)


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(f"{path}.invalid_type", "must be an object")
    return value


def _strict(raw: Mapping[str, Any], fields: frozenset[str] | tuple[str, ...], path: str) -> None:
    unknown = sorted((str(key) for key in raw if key not in fields))
    if unknown:
        raise _error(f"{path}.{unknown[0]}.unknown_field", "unknown field")


def _required(raw: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in raw:
        raise _error(f"{path}.{key}.required", "is required")
    return raw[key]


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value or "\0" in value or "\n" in value or "\r" in value:
        raise _error(f"{path}.invalid_type", "must be a non-empty single-line string")
    return value


def _boolean(value: Any, path: str) -> bool:
    if not isinstance(value, bool):
        raise _error(f"{path}.invalid_type", "must be a boolean")
    return value


def _positive(value: Any, path: str, *, allow_zero: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < (0 if allow_zero else 1):
        raise _error(f"{path}.invalid_type", "must be a non-negative integer" if allow_zero else "must be a positive integer")
    return value


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _root(value: Any) -> Path:
    text = _text(value, "profile.repository_root")
    candidate = Path(text)
    if not candidate.is_absolute():
        raise _error("profile.repository_root.not_absolute", "must be an absolute path")
    if not candidate.exists():
        raise _error("profile.repository_root.not_found", "does not exist")
    if not candidate.is_dir():
        raise _error("profile.repository_root.not_directory", "must be a directory")
    return candidate.resolve(strict=True)


def _base_branch(value: Any) -> str:
    branch = _text(value, "profile.base_branch")
    if any(char.isspace() for char in branch):
        raise _error("profile.base_branch.invalid_value", "must not contain whitespace")
    try:
        result = subprocess.run(["git", "check-ref-format", "--branch", branch], capture_output=True, check=False, shell=False, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _error("profile.base_branch.validation_failed", "Git branch validation could not run") from exc
    if result.returncode:
        raise _error("profile.base_branch.invalid_value", "is not a valid branch name")
    return branch


def _python(value: Any, root: Path) -> Path:
    text = _text(value, "profile.python_executable")
    candidate = Path(text) if Path(text).is_absolute() else root / text
    candidate = Path(os.path.abspath(os.fspath(candidate)))
    if not candidate.exists():
        raise _error("profile.python_executable.not_found", "does not exist")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_file():
        raise _error("profile.python_executable.not_file", "must be a file")
    if not os.access(candidate, os.X_OK):
        raise _error("profile.python_executable.not_executable", "must be executable")
    return candidate


def _existing_directory(value: Any, root: Path, path: str) -> Path:
    text = _text(value, path)
    candidate = Path(text) if Path(text).is_absolute() else root / text
    if not candidate.exists():
        raise _error(f"{path}.not_found", "does not exist")
    resolved = candidate.resolve(strict=True)
    if not resolved.is_dir():
        raise _error(f"{path}.not_directory", "must be a directory")
    if not _inside(resolved, root):
        raise _error(f"{path}.outside_repository", "must resolve inside repository_root")
    return resolved


def _validate_python_argv(argv: tuple[str, ...], path: str) -> None:
    args = argv[1:]
    if not args or "-c" in args or "-" in args or "-i" in args or "--interactive" in args:
        raise _error(f"{path}.python_operation_forbidden", "only -m pytest or -m py_compile is allowed")
    if len(args) < 2 or args[0] != "-m" or args[1] not in {"pytest", "py_compile"}:
        raise _error(f"{path}.python_operation_forbidden", "only -m pytest or -m py_compile is allowed")


def _git_subcommand(args: tuple[str, ...]) -> str | None:
    index = 0
    with_value = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"}
    while index < len(args):
        item = args[index]
        if item in with_value:
            index += 2
            continue
        if item.startswith("-"):
            index += 1
            continue
        return item
    return None


def _validate_git_argv(argv: tuple[str, ...], path: str) -> None:
    subcommand = _git_subcommand(argv[1:])
    allowed = {"diff", "status", "rev-parse", "show", "log", "ls-files", "ls-tree", "cat-file", "symbolic-ref"}
    if subcommand == "branch":
        rest = argv[argv.index("branch") + 1:]
        if not rest or not all(item in {"--show-current", "--list", "--contains", "--no-contains", "--merged", "--no-merged"} or not item.startswith("-") for item in rest):
            raise _error(f"{path}.git_operation_forbidden", "branch form is not read-only")
        return
    if subcommand not in allowed:
        raise _error(f"{path}.git_operation_forbidden", "Git subcommand is not allowed")


def _command(raw: Any, index: int, root: Path, python: Path, git: Path) -> ValidationCommand:
    path = f"profile.validation_commands[{index}]"
    value = _mapping(raw, path)
    _strict(value, _COMMAND_FIELDS, path)
    command_id = _text(_required(value, "command_id", path), f"{path}.command_id")
    kind = _text(_required(value, "kind", path), f"{path}.kind")
    if kind not in VALIDATION_COMMAND_KINDS:
        raise _error(f"{path}.kind.invalid_value", "unsupported validation command kind")
    raw_argv = _required(value, "argv", path)
    if not isinstance(raw_argv, list):
        raise _error(f"{path}.argv.invalid_type", "must be a list")
    if not raw_argv:
        raise _error(f"{path}.argv.empty", "must not be empty")
    argv = tuple(_text(item, f"{path}.argv[{position}]") for position, item in enumerate(raw_argv))
    executable = Path(argv[0])
    try:
        resolved_executable = (
            executable.resolve(strict=True)
            if executable.is_absolute()
            else None
        )
        resolved_python = python.resolve(strict=True)
    except OSError:
        resolved_executable = None
        resolved_python = None
    if argv[0] == str(python) or (
        resolved_executable is not None
        and resolved_executable == resolved_python
    ):
        normalized = (str(python), *argv[1:])
        _validate_python_argv(normalized, path)
    elif argv[0] == "git" or executable == git or resolved_executable == git:
        normalized = (str(git), *argv[1:])
        _validate_git_argv(normalized, path)
    else:
        raise _error(f"{path}.executable.not_allowed", "only configured Python and Git are allowed")
    return ValidationCommand(command_id, kind, normalized, str(_existing_directory(_required(value, "cwd", path), root, f"{path}.cwd")), _positive(_required(value, "timeout_seconds", path), f"{path}.timeout_seconds"), _boolean(_required(value, "required", path), f"{path}.required"), _boolean(_required(value, "stop_on_failure", path), f"{path}.stop_on_failure"))


def _future_path(value: Any, root: Path, path: str, outside: bool) -> Path:
    text = _text(value, path)
    candidate = Path(text) if Path(text).is_absolute() else root / text
    parent = candidate.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    try:
        resolved_parent = parent.resolve(strict=True)
    except OSError as exc:
        raise _error(f"{path}.invalid_path", "cannot resolve parent") from exc
    resolved = resolved_parent / candidate.relative_to(parent)
    if not _inside(resolved, root) and not outside:
        code = "symlink_escape" if candidate.parent.is_symlink() or parent != candidate.parent else "outside_repository"
        raise _error(f"{path}.{code}", "must resolve inside repository_root")
    return resolved


def _artifact(raw: Any, index: int, root: Path) -> ArtifactRequirement:
    path = f"profile.artifact_requirements[{index}]"
    value = _mapping(raw, path)
    _strict(value, _ARTIFACT_FIELDS, path)
    outside = _boolean(_required(value, "allow_outside_repository", path), f"{path}.allow_outside_repository")
    expected = _text(_required(value, "expected_type", path), f"{path}.expected_type")
    if expected not in ARTIFACT_EXPECTED_TYPES:
        raise _error(f"{path}.expected_type.invalid_value", "unsupported artifact type")
    minimum = _positive(_required(value, "minimum_size_bytes", path), f"{path}.minimum_size_bytes", allow_zero=True)
    parse_json = _boolean(_required(value, "parse_json", path), f"{path}.parse_json")
    raw_keys = _required(value, "required_keys", path)
    if not isinstance(raw_keys, list):
        raise _error(f"{path}.required_keys.invalid_type", "must be a list")
    keys = tuple(_text(key, f"{path}.required_keys[{number}]") for number, key in enumerate(raw_keys))
    if len(set(keys)) != len(keys):
        raise _error(f"{path}.required_keys.duplicate", "must not contain duplicates")
    readback = _boolean(_required(value, "readback_required", path), f"{path}.readback_required")
    checksum = _boolean(_required(value, "checksum_required", path), f"{path}.checksum_required")
    if parse_json and expected != "json":
        raise _error(f"{path}.parse_json.inconsistent", "requires expected_type json")
    if keys and (not parse_json or not readback):
        raise _error(f"{path}.required_keys.inconsistent", "requires parse_json and readback_required")
    if expected == "directory" and (minimum or parse_json or keys or checksum):
        suffix = "checksum_required" if checksum else "parse_json" if parse_json else "required_keys" if keys else "minimum_size_bytes"
        raise _error(f"{path}.{suffix}.inconsistent", "is incompatible with directory")
    return ArtifactRequirement(_text(_required(value, "artifact_id", path), f"{path}.artifact_id"), str(_future_path(_required(value, "path", path), root, f"{path}.path", outside)), _boolean(_required(value, "required", path), f"{path}.required"), expected, minimum, parse_json, tuple(sorted(keys)), readback, checksum, outside)


def _boundary(raw: Any) -> ApprovalBoundary:
    value = _mapping(raw, "profile.approval_boundary")
    _strict(value, APPROVAL_ACTIONS, "profile.approval_boundary")
    values: dict[str, str] = {}
    for action in APPROVAL_ACTIONS:
        mode = _text(_required(value, action, "profile.approval_boundary"), f"profile.approval_boundary.{action}")
        if mode not in APPROVAL_MODES:
            raise _error(f"profile.approval_boundary.{action}.invalid_value", "unsupported approval mode")
        values[action] = mode
    return ApprovalBoundary(**values)


def _profile_mapping(profile: RepositoryProfile) -> dict[str, Any]:
    return {
        "schema_version": profile.schema_version, "profile_id": profile.profile_id,
        "repository_root": profile.repository_root, "base_branch": profile.base_branch,
        "python_executable": profile.python_executable,
        "validation_commands": [{"command_id": item.command_id, "kind": item.kind, "argv": list(item.argv), "cwd": item.cwd, "timeout_seconds": item.timeout_seconds, "required": item.required, "stop_on_failure": item.stop_on_failure} for item in profile.validation_commands],
        "artifact_requirements": [{"artifact_id": item.artifact_id, "path": item.path, "required": item.required, "expected_type": item.expected_type, "minimum_size_bytes": item.minimum_size_bytes, "parse_json": item.parse_json, "required_keys": list(item.required_keys), "readback_required": item.readback_required, "checksum_required": item.checksum_required, "allow_outside_repository": item.allow_outside_repository} for item in profile.artifact_requirements],
        "forbidden_git_operations": list(profile.forbidden_git_operations), "max_changed_files": profile.max_changed_files,
        "approval_boundary": asdict(profile.approval_boundary), "environment_allowlist": list(profile.environment_allowlist),
    }


def validate_repository_profile(profile: Mapping[str, Any] | RepositoryProfile) -> RepositoryProfile:
    """Strictly validate a Profile declaration; this never authorizes execution."""
    raw: Mapping[str, Any] = _profile_mapping(profile) if isinstance(profile, RepositoryProfile) else _mapping(profile, "profile")
    _strict(raw, _ROOT_FIELDS, "profile")
    version = _text(_required(raw, "schema_version", "profile"), "profile.schema_version")
    if version != REPOSITORY_PROFILE_SCHEMA_VERSION:
        raise _error("profile.schema_version.unsupported", "must be '1'")
    root = _root(_required(raw, "repository_root", "profile"))
    python = _python(_required(raw, "python_executable", "profile"), root)
    git_value = shutil.which("git")
    if not git_value:
        raise _error("profile.validation_commands.git.executable_not_found", "Git executable is unavailable")
    git = Path(git_value).resolve()
    commands_raw = _required(raw, "validation_commands", "profile")
    if not isinstance(commands_raw, list):
        raise _error("profile.validation_commands.invalid_type", "must be a list")
    commands = [_command(value, index, root, python, git) for index, value in enumerate(commands_raw)]
    ids: set[str] = set(); kinds: set[str] = set()
    for index, command in enumerate(commands):
        if command.command_id in ids:
            raise _error(f"profile.validation_commands[{index}].command_id.duplicate", "duplicate command ID")
        if command.kind in kinds:
            raise _error(f"profile.validation_commands[{index}].kind.duplicate", "duplicate command kind")
        ids.add(command.command_id); kinds.add(command.kind)
    missing = next((kind for kind in VALIDATION_COMMAND_KINDS if kind not in kinds), None)
    if missing:
        raise _error("profile.validation_commands.missing_kind", f"missing {missing}")
    artifacts_raw = _required(raw, "artifact_requirements", "profile")
    if not isinstance(artifacts_raw, list):
        raise _error("profile.artifact_requirements.invalid_type", "must be a list")
    artifacts = [_artifact(value, index, root) for index, value in enumerate(artifacts_raw)]
    artifact_ids: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if artifact.artifact_id in artifact_ids:
            raise _error(f"profile.artifact_requirements[{index}].artifact_id.duplicate", "duplicate artifact ID")
        artifact_ids.add(artifact.artifact_id)
    forbidden_raw = _required(raw, "forbidden_git_operations", "profile")
    if not isinstance(forbidden_raw, list):
        raise _error("profile.forbidden_git_operations.invalid_type", "must be a list")
    forbidden: set[str] = set()
    for index, item in enumerate(forbidden_raw):
        value = _text(item, f"profile.forbidden_git_operations[{index}]")
        if value not in FORBIDDEN_GIT_OPERATION_IDS:
            raise _error(f"profile.forbidden_git_operations[{index}].invalid_value", "unsupported operation")
        if value in forbidden:
            raise _error(f"profile.forbidden_git_operations[{index}].duplicate", "duplicate operation")
        forbidden.add(value)
    if any(item not in forbidden for item in FORBIDDEN_GIT_OPERATION_IDS):
        raise _error("profile.forbidden_git_operations.missing_required", "all required operations are required")
    allow_raw = _required(raw, "environment_allowlist", "profile")
    if not isinstance(allow_raw, list):
        raise _error("profile.environment_allowlist.invalid_type", "must be a list")
    allow: set[str] = set()
    for index, item in enumerate(allow_raw):
        value = _text(item, f"profile.environment_allowlist[{index}]")
        if not _NAME.fullmatch(value):
            raise _error(f"profile.environment_allowlist[{index}].invalid_value", "must be an environment variable name")
        if value in allow:
            raise _error(f"profile.environment_allowlist[{index}].duplicate", "duplicate environment variable")
        allow.add(value)
    return RepositoryProfile(version, _text(_required(raw, "profile_id", "profile"), "profile.profile_id"), str(root), _base_branch(_required(raw, "base_branch", "profile")), str(python), tuple(sorted(commands, key=lambda item: VALIDATION_COMMAND_KINDS.index(item.kind))), tuple(sorted(artifacts, key=lambda item: item.artifact_id)), tuple(item for item in FORBIDDEN_GIT_OPERATION_IDS if item in forbidden), _positive(_required(raw, "max_changed_files", "profile"), "profile.max_changed_files"), _boundary(_required(raw, "approval_boundary", "profile")), tuple(sorted(allow)))


def load_repository_profile(profile_path: str | os.PathLike[str]) -> RepositoryProfile:
    """Load one UTF-8 JSON profile, then apply strict validation."""
    if isinstance(profile_path, bool) or not isinstance(profile_path, (str, os.PathLike)):
        raise _error("profile_file.invalid_type", "must be a text path")
    value = os.fspath(profile_path)
    if isinstance(value, bytes) or not value.strip():
        raise _error("profile_file.invalid_type", "must be a non-empty text path")
    path = Path(value)
    if not path.exists():
        raise _error("profile_file.not_found", "does not exist")
    if not path.is_file():
        raise _error("profile_file.not_file", "must be a file")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        raise _error("profile_file.read_failed", "is not UTF-8 text") from exc
    except OSError as exc:
        raise _error("profile_file.read_failed", "could not be read") from exc
    except json.JSONDecodeError as exc:
        raise _error("profile_file.json_invalid", "is not valid JSON") from exc
    if not isinstance(raw, Mapping):
        raise _error("profile_file.root.invalid_type", "JSON root must be an object")
    return validate_repository_profile(raw)


def repository_profile_to_mapping(profile: RepositoryProfile) -> dict[str, Any]:
    if not isinstance(profile, RepositoryProfile):
        raise TypeError("profile must be a RepositoryProfile")
    return _profile_mapping(profile)


def serialize_repository_profile(profile: RepositoryProfile) -> str:
    return json.dumps(repository_profile_to_mapping(profile), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


__all__ = ["APPROVAL_ACTIONS", "APPROVAL_MODES", "ARTIFACT_EXPECTED_TYPES", "FORBIDDEN_GIT_OPERATION_IDS", "REPOSITORY_PROFILE_SCHEMA_VERSION", "VALIDATION_COMMAND_KINDS", "ApprovalBoundary", "ArtifactRequirement", "RepositoryProfile", "RepositoryProfileValidationError", "ValidationCommand", "load_repository_profile", "repository_profile_to_mapping", "serialize_repository_profile", "validate_repository_profile"]

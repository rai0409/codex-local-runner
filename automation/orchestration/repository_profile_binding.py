"""Bind a validated source RepositoryProfile to one prepared Git worktree."""
from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Any

from automation.orchestration.repository_profile import RepositoryProfile
from automation.orchestration.repository_profile import validate_repository_profile


class RepositoryProfileBindingError(ValueError):
    """Stable, secret-free worktree Profile binding failure."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def _error(code: str, message: str) -> RepositoryProfileBindingError:
    return RepositoryProfileBindingError(code, message)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _rebind_inside(
    source_path: str, source_root: Path, worktree: Path, code: str, *, directory: bool
) -> str:
    try:
        relative = Path(source_path).resolve(strict=True).relative_to(source_root)
    except (OSError, ValueError) as exc:
        raise _error(code, "source path must resolve inside repository root") from exc
    target = worktree / relative
    if not target.exists():
        raise _error(f"{code}.not_found", "mapped worktree path does not exist")
    resolved = target.resolve(strict=True)
    if directory and not resolved.is_dir():
        raise _error(f"{code}.not_directory", "mapped worktree path must be a directory")
    if not _inside(resolved, worktree):
        raise _error(f"{code}.symlink_escape", "mapped worktree path escapes worktree")
    return str(resolved)


def bind_repository_profile_to_worktree(
    profile: RepositoryProfile, worktree_path: str | os.PathLike[str]
) -> RepositoryProfile:
    """Return a fresh validated Profile whose repository paths target the worktree."""
    source = validate_repository_profile(profile)
    if isinstance(worktree_path, bool) or not isinstance(worktree_path, (str, os.PathLike)):
        raise _error("profile_binding.worktree.invalid_type", "worktree must be a path")
    raw = os.fspath(worktree_path)
    if isinstance(raw, bytes) or not raw.strip():
        raise _error("profile_binding.worktree.invalid_type", "worktree must be a non-empty text path")
    worktree = Path(raw)
    if not worktree.is_absolute():
        raise _error("profile_binding.worktree.not_absolute", "worktree must be absolute")
    if not worktree.exists():
        raise _error("profile_binding.worktree.not_found", "worktree does not exist")
    worktree = worktree.resolve(strict=True)
    if not worktree.is_dir():
        raise _error("profile_binding.worktree.not_directory", "worktree must be a directory")
    if not (worktree / ".git").exists():
        raise _error("profile_binding.worktree.not_git_worktree", "worktree is not a Git worktree")
    source_root = Path(source.repository_root).resolve(strict=True)
    commands: list[dict[str, Any]] = []
    for command in source.validation_commands:
        commands.append({"command_id": command.command_id, "kind": command.kind,
            "argv": list(command.argv),
            "cwd": _rebind_inside(command.cwd, source_root, worktree, "profile_binding.command_cwd", directory=True),
            "timeout_seconds": command.timeout_seconds, "required": command.required,
            "stop_on_failure": command.stop_on_failure})
    artifacts: list[dict[str, Any]] = []
    for artifact in source.artifact_requirements:
        item = asdict(artifact)
        item["required_keys"] = list(artifact.required_keys)
        if not artifact.allow_outside_repository:
            item["path"] = _rebind_inside(artifact.path, source_root, worktree, "profile_binding.artifact_path", directory=False)
        artifacts.append(item)
    return validate_repository_profile({"schema_version": source.schema_version,
        "profile_id": source.profile_id, "repository_root": str(worktree),
        "base_branch": source.base_branch, "python_executable": source.python_executable,
        "validation_commands": commands, "artifact_requirements": artifacts,
        "forbidden_git_operations": list(source.forbidden_git_operations),
        "max_changed_files": source.max_changed_files,
        "approval_boundary": asdict(source.approval_boundary),
        "environment_allowlist": list(source.environment_allowlist),
        **({"execution_timeout_seconds": source.execution_timeout_seconds}
           if source.execution_timeout_seconds is not None else {})})


__all__ = ["RepositoryProfileBindingError", "bind_repository_profile_to_worktree"]

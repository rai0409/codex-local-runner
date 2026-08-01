"""Read-only, deterministic Git repository state inspection."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any

REPOSITORY_STATE_SCHEMA_VERSION = "1"
WORKTREE_STATES = ("known_clean", "known_dirty")
OPERATION_ORDER = ("merge", "rebase", "cherry_pick", "revert", "bisect", "sequencer")
_TIMEOUT_SECONDS = 10


class RepositoryStateAnalyzerError(ValueError):
    """Failure with a stable machine-readable reason code."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


@dataclass(frozen=True)
class RepositoryStateSnapshot:
    schema_version: str
    repository_root: str
    branch: str | None
    head_sha: str | None
    detached_head: bool
    upstream_ref: str | None
    ahead_count: int | None
    behind_count: int | None
    tracked_modified_files: tuple[str, ...]
    staged_files: tuple[str, ...]
    untracked_files: tuple[str, ...]
    conflicted_files: tuple[str, ...]
    worktree_state: str
    operations_in_progress: tuple[str, ...]


def _error(reason_code: str, message: str) -> RepositoryStateAnalyzerError:
    return RepositoryStateAnalyzerError(reason_code, message)


def _path(repository_path: str | os.PathLike[str]) -> str:
    if isinstance(repository_path, bool) or not isinstance(repository_path, (str, os.PathLike)):
        raise _error("repository_path.invalid_type", "must be a non-empty path string or PathLike")
    value = os.fspath(repository_path)
    if isinstance(value, bytes) or not value.strip():
        raise _error("repository_path.invalid_type", "must be a non-empty text path")
    candidate = Path(value)
    if not candidate.exists():
        raise _error("repository_path.not_found", "does not exist")
    if not candidate.is_dir():
        raise _error("repository_path.not_directory", "must be a directory")
    return str(candidate.absolute())


def _run_git(repository_path: str, args: list[str], *, purpose: str, allow_failure: bool = False) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", "-C", repository_path, *args],
            capture_output=True,
            check=False,
            shell=False,
            timeout=_TIMEOUT_SECONDS,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except FileNotFoundError as exc:
        raise _error("git.executable_not_found", "git executable is unavailable") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise _error("git.command_failed", f"{purpose} could not be executed") from exc
    if result.returncode and not allow_failure:
        raise _error("git.command_failed", f"{purpose} exited with code {result.returncode}")
    return result


def _text(value: bytes, *, purpose: str) -> str:
    try:
        return value.decode("utf-8", "surrogateescape").strip()
    except UnicodeError as exc:
        raise _error("git.output_invalid", f"{purpose} output could not be decoded") from exc


def _nul_paths(output: bytes) -> tuple[str, ...]:
    return tuple(sorted({os.fsdecode(item) for item in output.split(b"\0") if item}))


def _branch_and_head(repository_path: str) -> tuple[str | None, str | None, bool]:
    branch_result = _run_git(repository_path, ["symbolic-ref", "--quiet", "--short", "HEAD"], purpose="branch lookup", allow_failure=True)
    if branch_result.returncode not in (0, 1):
        raise _error("git.command_failed", f"branch lookup exited with code {branch_result.returncode}")
    branch = _text(branch_result.stdout, purpose="branch lookup") if branch_result.returncode == 0 else None
    head_result = _run_git(repository_path, ["rev-parse", "--verify", "HEAD"], purpose="HEAD lookup", allow_failure=True)
    if head_result.returncode not in (0, 128):
        raise _error("git.command_failed", f"HEAD lookup exited with code {head_result.returncode}")
    head = _text(head_result.stdout, purpose="HEAD lookup") if head_result.returncode == 0 else None
    if head is not None and (len(head) != 40 or any(char not in "0123456789abcdef" for char in head)):
        raise _error("git.output_invalid", "HEAD lookup did not return a full SHA")
    if branch is None and head is None:
        raise _error("git.output_invalid", "repository has neither a symbolic branch nor HEAD")
    return branch, head, branch is None


def _upstream(repository_path: str, branch: str | None, head: str | None) -> tuple[str | None, int | None, int | None]:
    if branch is None or head is None:
        return None, None, None
    remote = _run_git(repository_path, ["config", "--get", f"branch.{branch}.remote"], purpose="upstream remote lookup", allow_failure=True)
    merge = _run_git(repository_path, ["config", "--get", f"branch.{branch}.merge"], purpose="upstream merge lookup", allow_failure=True)
    if remote.returncode not in (0, 1) or merge.returncode not in (0, 1):
        raise _error("git.command_failed", "upstream configuration lookup failed")
    if remote.returncode or merge.returncode:
        return None, None, None
    remote_name, merge_ref = _text(remote.stdout, purpose="upstream remote lookup"), _text(merge.stdout, purpose="upstream merge lookup")
    if not remote_name or not merge_ref:
        return None, None, None
    short_merge = merge_ref.removeprefix("refs/heads/")
    upstream = short_merge if remote_name == "." else f"{remote_name}/{short_merge}"
    count = _run_git(repository_path, ["rev-list", "--left-right", "--count", f"HEAD...@{{upstream}}"], purpose="ahead behind lookup", allow_failure=True)
    if count.returncode:
        return upstream, None, None
    tokens = _text(count.stdout, purpose="ahead behind lookup").split()
    if len(tokens) != 2 or not all(token.isdigit() for token in tokens):
        raise _error("git.output_invalid", "ahead behind lookup did not return two counts")
    ahead, behind = (int(token) for token in tokens)
    return upstream, ahead, behind


def _status(repository_path: str) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    output = _run_git(repository_path, ["status", "--porcelain=v2", "-z", "--untracked-files=all"], purpose="status lookup").stdout
    staged: set[str] = set()
    modified: set[str] = set()
    untracked: set[str] = set()
    conflicted: set[str] = set()
    records = output.split(b"\0")
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        kind = record[:2]
        if kind == b"? ":
            untracked.add(os.fsdecode(record[2:]))
            continue
        if kind == b"u ":
            fields = record.split(b" ", 10)
            if len(fields) != 11:
                raise _error("git.output_invalid", "unmerged status record is malformed")
            conflicted.add(os.fsdecode(fields[10]))
            continue
        if kind == b"1 ":
            fields = record.split(b" ", 8)
            if len(fields) != 9:
                raise _error("git.output_invalid", "ordinary status record is malformed")
            xy, path = fields[1], os.fsdecode(fields[8])
        elif kind == b"2 ":
            fields = record.split(b" ", 9)
            if len(fields) != 10 or index >= len(records):
                raise _error("git.output_invalid", "rename status record is malformed")
            xy, path = fields[1], os.fsdecode(fields[9])
            index += 1  # original path; contract retains destination only
        else:
            continue
        if len(xy) != 2:
            raise _error("git.output_invalid", "status code is malformed")
        if xy[:1] != b".":
            staged.add(path)
        if xy[1:] != b".":
            modified.add(path)
    return tuple(sorted(modified)), tuple(sorted(staged)), tuple(sorted(untracked)), tuple(sorted(conflicted))


def _operations(repository_path: str, repository_root: str) -> tuple[str, ...]:
    probes = {
        "merge": ("MERGE_HEAD",), "rebase": ("rebase-merge", "rebase-apply"),
        "cherry_pick": ("CHERRY_PICK_HEAD",), "revert": ("REVERT_HEAD",),
        "bisect": ("BISECT_LOG",), "sequencer": ("sequencer",),
    }
    found: list[str] = []
    for operation in OPERATION_ORDER:
        exists = False
        for name in probes[operation]:
            result = _run_git(repository_path, ["rev-parse", "--git-path", name], purpose=f"{operation} marker lookup")
            path = Path(_text(result.stdout, purpose=f"{operation} marker lookup"))
            if not path.is_absolute():
                path = Path(repository_root) / path
            exists = exists or path.exists()
        if exists:
            found.append(operation)
    return tuple(found)


def analyze_repository_state(repository_path: str | os.PathLike[str]) -> RepositoryStateSnapshot:
    """Collect a complete repository snapshot without changing repository state."""
    path = _path(repository_path)
    root_result = _run_git(path, ["rev-parse", "--show-toplevel"], purpose="repository root lookup", allow_failure=True)
    if root_result.returncode:
        raise _error("repository.invalid_git_repository", "path is not inside a Git work tree")
    root = _text(root_result.stdout, purpose="repository root lookup")
    if not root or not Path(root).is_absolute():
        raise _error("git.output_invalid", "repository root lookup did not return an absolute path")
    branch, head, detached = _branch_and_head(root)
    upstream, ahead, behind = _upstream(root, branch, head)
    modified, staged, untracked, conflicted = _status(root)
    operations = _operations(root, root)
    worktree_state = "known_dirty" if any((modified, staged, untracked, conflicted)) else "known_clean"
    return RepositoryStateSnapshot(REPOSITORY_STATE_SCHEMA_VERSION, root, branch, head, detached, upstream, ahead, behind, modified, staged, untracked, conflicted, worktree_state, operations)


def repository_state_to_mapping(snapshot: RepositoryStateSnapshot) -> dict[str, Any]:
    if not isinstance(snapshot, RepositoryStateSnapshot):
        raise TypeError("snapshot must be a RepositoryStateSnapshot")
    return {
        "schema_version": snapshot.schema_version, "repository_root": snapshot.repository_root,
        "branch": snapshot.branch, "head_sha": snapshot.head_sha, "detached_head": snapshot.detached_head,
        "upstream_ref": snapshot.upstream_ref, "ahead_count": snapshot.ahead_count, "behind_count": snapshot.behind_count,
        "tracked_modified_files": list(snapshot.tracked_modified_files), "staged_files": list(snapshot.staged_files),
        "untracked_files": list(snapshot.untracked_files), "conflicted_files": list(snapshot.conflicted_files),
        "worktree_state": snapshot.worktree_state, "operations_in_progress": list(snapshot.operations_in_progress),
    }


def serialize_repository_state(snapshot: RepositoryStateSnapshot) -> str:
    return json.dumps(repository_state_to_mapping(snapshot), ensure_ascii=True, sort_keys=True, separators=(",", ":"))


__all__ = ["RepositoryStateAnalyzerError", "RepositoryStateSnapshot", "analyze_repository_state", "repository_state_to_mapping", "serialize_repository_state"]

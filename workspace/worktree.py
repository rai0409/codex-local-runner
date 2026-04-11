from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class PrepareGitWorktreeResult(TypedDict):
    source_repo_path: str
    worktree_path: str
    branch_name: str
    created: bool
    cleanup_needed: bool
    error: str


class CleanupGitWorktreeResult(TypedDict):
    worktree_path: str
    branch_name: str
    cleaned: bool
    error: str


def _run_git(source_repo_path: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", source_repo_path, *args],
        text=True,
        capture_output=True,
    )


def prepare_git_worktree(source_repo_path: str, worktree_parent: str) -> PrepareGitWorktreeResult:
    source_path = Path(source_repo_path).expanduser()
    normalized_source = str(source_path)

    if not source_path.exists():
        return {
            "source_repo_path": normalized_source,
            "worktree_path": "",
            "branch_name": "",
            "created": False,
            "cleanup_needed": False,
            "error": f"source repo path does not exist: {source_path}",
        }
    if not source_path.is_dir():
        return {
            "source_repo_path": normalized_source,
            "worktree_path": "",
            "branch_name": "",
            "created": False,
            "cleanup_needed": False,
            "error": f"source repo path is not a directory: {source_path}",
        }

    check = _run_git(normalized_source, ["rev-parse", "--is-inside-work-tree"])
    if check.returncode != 0:
        error_text = (check.stderr or check.stdout or "not a git working tree").strip()
        return {
            "source_repo_path": normalized_source,
            "worktree_path": "",
            "branch_name": "",
            "created": False,
            "cleanup_needed": False,
            "error": f"source repo path is not a git working tree: {error_text}",
        }

    parent = Path(worktree_parent)
    parent.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    attempts = 100
    for index in range(attempts):
        suffix = "" if index == 0 else f"_{index}"
        worktree_path = parent / f"{stamp}{suffix}"
        branch_suffix = "" if index == 0 else f"-{index}"
        branch_name = f"codex-run/{stamp}{branch_suffix}"

        add = _run_git(
            normalized_source,
            ["worktree", "add", "-b", branch_name, str(worktree_path), "HEAD"],
        )
        if add.returncode == 0:
            return {
                "source_repo_path": normalized_source,
                "worktree_path": str(worktree_path),
                "branch_name": branch_name,
                "created": True,
                "cleanup_needed": True,
                "error": "",
            }

    last_error = (add.stderr or add.stdout or "failed to create git worktree").strip()
    return {
        "source_repo_path": normalized_source,
        "worktree_path": "",
        "branch_name": "",
        "created": False,
        "cleanup_needed": False,
        "error": f"failed to create git worktree: {last_error}",
    }


def cleanup_git_worktree(
    source_repo_path: str,
    worktree_path: str,
    branch_name: str,
) -> CleanupGitWorktreeResult:
    normalized_source = str(Path(source_repo_path).expanduser())
    errors: list[str] = []

    if worktree_path:
        remove = _run_git(normalized_source, ["worktree", "remove", worktree_path, "--force"])
        if remove.returncode != 0:
            errors.append((remove.stderr or remove.stdout or "failed to remove worktree").strip())

    if branch_name:
        delete = _run_git(normalized_source, ["branch", "-D", branch_name])
        if delete.returncode != 0:
            errors.append((delete.stderr or delete.stdout or "failed to delete branch").strip())

    return {
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "cleaned": len(errors) == 0,
        "error": " | ".join(error for error in errors if error),
    }

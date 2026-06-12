from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

_MAIN_REPO_ROOT = Path(__file__).resolve().parents[3]
_SANDBOX_ROOT_PREFIXES = ("/tmp/",)
GENERATED_FILE_SUFFIXES = {".pyc", ".pyo"}
GENERATED_DIR_NAME = "__pycache__"


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "blocked_reason": reason,
        "removed_count": 0,
        "removed_paths": [],
    }


def cleanup_generated_python_artifacts(repo_path: str | Path | None) -> dict[str, Any]:
    """Remove ONLY Python bytecode artifacts (__pycache__/, *.pyc, *.pyo) inside a
    /tmp sandbox repo. Refuses empty paths, the filesystem root, anything outside
    /tmp, and the main repo (paths are resolved before any decision). Symlinks are
    never followed or deleted through. Normal source files are never touched.
    """
    text = str(repo_path or "").strip()
    if not text:
        return _blocked("empty_path")
    repo = Path(text).resolve()
    if repo == Path("/"):
        return _blocked("root_path")
    repo_text = repo.as_posix()
    if not any(repo_text.startswith(prefix) for prefix in _SANDBOX_ROOT_PREFIXES):
        return _blocked("path_not_sandbox")
    main_root = _MAIN_REPO_ROOT.resolve()
    if repo == main_root or main_root in repo.parents or repo in main_root.parents:
        return _blocked("main_repo_path")
    if not repo.is_dir():
        return _blocked("path_not_directory")

    generated_files: list[Path] = []
    generated_dirs: list[Path] = []
    for entry in repo.rglob("*"):
        if entry.is_symlink():
            continue
        if entry.is_file() and entry.suffix in GENERATED_FILE_SUFFIXES:
            generated_files.append(entry)
        elif entry.is_dir() and entry.name == GENERATED_DIR_NAME:
            generated_dirs.append(entry)

    removed_paths: list[str] = []
    for entry in generated_files:
        # a pyc inside a __pycache__ dir is removed with its directory below
        if any(parent.name == GENERATED_DIR_NAME for parent in entry.parents):
            continue
        entry.unlink(missing_ok=True)
        removed_paths.append(entry.relative_to(repo).as_posix())
    for entry in generated_dirs:
        if entry.exists():
            shutil.rmtree(entry)
            removed_paths.append(entry.relative_to(repo).as_posix() + "/")

    return {
        "status": "success",
        "blocked_reason": "none",
        "removed_count": len(removed_paths),
        "removed_paths": sorted(removed_paths),
    }


def evaluate_sandbox_cleanliness(repo_path: str | Path) -> dict[str, Any]:
    """Compute the post-run cleanliness of a sandbox repo via `git status --short`."""
    repo = Path(repo_path)
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "sandbox_final_status_clean": False,
            "sandbox_final_status_short": [f"git_status_failed: {completed.stderr.strip()}"],
            "sandbox_untracked_after_cleanup": [],
        }
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    untracked = [line[3:].strip() for line in lines if line.startswith("??")]
    return {
        "sandbox_final_status_clean": not lines,
        "sandbox_final_status_short": lines,
        "sandbox_untracked_after_cleanup": untracked,
    }


__all__ = [
    "GENERATED_DIR_NAME",
    "GENERATED_FILE_SUFFIXES",
    "cleanup_generated_python_artifacts",
    "evaluate_sandbox_cleanliness",
]

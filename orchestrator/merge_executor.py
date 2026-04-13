from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run_git(repo_path: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", repo_path, *args],
        text=True,
        capture_output=True,
    )


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_ref(ref: str) -> str:
    normalized = str(ref).strip()
    if not normalized:
        return ""
    if normalized.startswith("refs/"):
        return normalized
    return f"refs/heads/{normalized}"


def _normalize_sha(value: str) -> str:
    return str(value).strip()


def execute_constrained_merge(
    *,
    repo_path: str,
    target_ref: str,
    source_sha: str,
    base_sha: str,
) -> dict[str, Any]:
    attempted_at = _now_utc_iso()
    normalized_repo = str(Path(repo_path).expanduser())
    normalized_target_ref = _normalize_ref(target_ref)
    normalized_source_sha = _normalize_sha(source_sha)
    normalized_base_sha = _normalize_sha(base_sha)

    result: dict[str, Any] = {
        "status": "skipped",
        "attempted": False,
        "attempted_at": attempted_at,
        "pre_merge_sha": None,
        "post_merge_sha": None,
        "merge_result_sha": None,
        "error": None,
    }

    repo_dir = Path(normalized_repo)
    if not repo_dir.exists() or not repo_dir.is_dir():
        result["error"] = f"repo_path is not a directory: {normalized_repo}"
        return result

    inside_worktree = _run_git(normalized_repo, ["rev-parse", "--is-inside-work-tree"])
    if inside_worktree.returncode != 0:
        result["error"] = (
            inside_worktree.stderr or inside_worktree.stdout or "not a git working tree"
        ).strip()
        return result

    head_result = _run_git(normalized_repo, ["rev-parse", "HEAD"])
    if head_result.returncode != 0:
        result["error"] = (head_result.stderr or head_result.stdout or "failed to read HEAD").strip()
        return result
    pre_merge_sha = (head_result.stdout or "").strip()
    result["pre_merge_sha"] = pre_merge_sha

    if not normalized_target_ref:
        result["error"] = "target_ref is required"
        return result
    if not normalized_source_sha:
        result["error"] = "source_sha is required"
        return result
    if not normalized_base_sha:
        result["error"] = "base_sha is required"
        return result

    target_head_result = _run_git(normalized_repo, ["rev-parse", normalized_target_ref])
    if target_head_result.returncode != 0:
        result["error"] = (
            target_head_result.stderr or target_head_result.stdout or "failed to resolve target_ref"
        ).strip()
        return result
    target_head_sha = (target_head_result.stdout or "").strip()

    if target_head_sha != pre_merge_sha:
        result["error"] = "target_ref_drift_detected"
        return result

    if normalized_base_sha != pre_merge_sha:
        result["error"] = "base_sha_mismatch"
        return result

    source_exists = _run_git(normalized_repo, ["rev-parse", f"{normalized_source_sha}^{{commit}}"])
    if source_exists.returncode != 0:
        result["error"] = (
            source_exists.stderr or source_exists.stdout or "failed to resolve source_sha"
        ).strip()
        return result

    source_already_merged = _run_git(
        normalized_repo,
        ["merge-base", "--is-ancestor", normalized_source_sha, pre_merge_sha],
    )
    if source_already_merged.returncode == 0:
        result["error"] = "source_already_merged_into_target"
        return result
    if source_already_merged.returncode not in {1}:
        result["error"] = (
            source_already_merged.stderr
            or source_already_merged.stdout
            or "failed to evaluate merge-base invariant"
        ).strip()
        return result

    merge_result = _run_git(
        normalized_repo,
        [
            "-c",
            "user.name=Codex Merge",
            "-c",
            "user.email=codex-merge@example.com",
            "merge",
            "--no-ff",
            "--no-edit",
            normalized_source_sha,
        ],
    )
    result["attempted"] = True

    if merge_result.returncode != 0:
        _run_git(normalized_repo, ["merge", "--abort"])
        result["status"] = "failed"
        result["error"] = (merge_result.stderr or merge_result.stdout or "git merge failed").strip()
        post_failure = _run_git(normalized_repo, ["rev-parse", "HEAD"])
        if post_failure.returncode == 0:
            result["post_merge_sha"] = (post_failure.stdout or "").strip()
        return result

    post_result = _run_git(normalized_repo, ["rev-parse", "HEAD"])
    if post_result.returncode != 0:
        result["status"] = "failed"
        result["error"] = (
            post_result.stderr or post_result.stdout or "merge succeeded but failed to read HEAD"
        ).strip()
        return result

    post_merge_sha = (post_result.stdout or "").strip()
    result["post_merge_sha"] = post_merge_sha

    if not post_merge_sha or post_merge_sha == pre_merge_sha:
        result["status"] = "failed"
        result["error"] = "merge_did_not_produce_new_commit"
        return result

    result["status"] = "succeeded"
    result["merge_result_sha"] = post_merge_sha
    result["error"] = None
    return result

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


def execute_constrained_rollback(
    *,
    repo_path: str,
    target_ref: str,
    pre_merge_sha: str,
    post_merge_sha: str,
) -> dict[str, Any]:
    attempted_at = _now_utc_iso()
    normalized_repo = str(Path(repo_path).expanduser())
    normalized_target_ref = _normalize_ref(target_ref)
    normalized_pre_sha = _normalize_sha(pre_merge_sha)
    normalized_post_sha = _normalize_sha(post_merge_sha)

    result: dict[str, Any] = {
        "status": "skipped",
        "attempted": False,
        "attempted_at": attempted_at,
        "consistency_check_passed": False,
        "current_head_sha": None,
        "rollback_result_sha": None,
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
    current_head_sha = (head_result.stdout or "").strip()
    result["current_head_sha"] = current_head_sha

    if not normalized_target_ref:
        result["error"] = "target_ref is required"
        return result
    if not normalized_pre_sha:
        result["error"] = "pre_merge_sha is required"
        return result
    if not normalized_post_sha:
        result["error"] = "post_merge_sha is required"
        return result

    target_head_result = _run_git(normalized_repo, ["rev-parse", normalized_target_ref])
    if target_head_result.returncode != 0:
        result["error"] = (
            target_head_result.stderr or target_head_result.stdout or "failed to resolve target_ref"
        ).strip()
        return result
    target_head_sha = (target_head_result.stdout or "").strip()

    if target_head_sha != current_head_sha:
        result["error"] = "target_ref_drift_detected"
        return result

    if current_head_sha != normalized_post_sha:
        result["error"] = "current_head_mismatch_post_merge"
        return result

    post_exists = _run_git(normalized_repo, ["rev-parse", f"{normalized_post_sha}^{{commit}}"])
    if post_exists.returncode != 0:
        result["error"] = (
            post_exists.stderr or post_exists.stdout or "failed to resolve post_merge_sha"
        ).strip()
        return result

    result["consistency_check_passed"] = True

    rollback_result = _run_git(
        normalized_repo,
        [
            "-c",
            "user.name=Codex Rollback",
            "-c",
            "user.email=codex-rollback@example.com",
            "revert",
            "--no-edit",
            "-m",
            "1",
            normalized_post_sha,
        ],
    )
    result["attempted"] = True

    if rollback_result.returncode != 0:
        _run_git(normalized_repo, ["revert", "--abort"])
        result["status"] = "failed"
        result["error"] = (
            rollback_result.stderr or rollback_result.stdout or "git revert failed"
        ).strip()
        post_failure = _run_git(normalized_repo, ["rev-parse", "HEAD"])
        if post_failure.returncode == 0:
            result["rollback_result_sha"] = (post_failure.stdout or "").strip()
        return result

    post_result = _run_git(normalized_repo, ["rev-parse", "HEAD"])
    if post_result.returncode != 0:
        result["status"] = "failed"
        result["error"] = (
            post_result.stderr or post_result.stdout or "rollback succeeded but failed to read HEAD"
        ).strip()
        return result

    rollback_sha = (post_result.stdout or "").strip()
    result["rollback_result_sha"] = rollback_sha
    if not rollback_sha or rollback_sha == current_head_sha:
        result["status"] = "failed"
        result["error"] = "rollback_did_not_produce_new_commit"
        return result

    result["status"] = "succeeded"
    result["error"] = None
    return result

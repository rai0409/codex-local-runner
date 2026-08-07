"""Fail-closed, local-only controller for one repository-resolved task.

The controller deliberately owns Git mutation only after Registry resolution,
Profile approvals, source preflight, prepared-worktree execution, validation,
and exact change-scope checks have all succeeded.  It never performs remote
operations and preserves unsafe worktrees for inspection instead of repairing
them.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from adapters import resolve_adapter
from automation.orchestration.repository_profile_binding import bind_repository_profile_to_worktree
from automation.orchestration.repository_registry import (
    DEFAULT_REPOSITORY_BINDINGS_PATH,
    load_repository_registry,
    resolve_repository,
)
from automation.orchestration.repository_single_task_spec import load_repository_single_task_spec
from automation.orchestration.repository_state_analyzer import analyze_repository_state, repository_state_to_mapping


DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT = (
    "~/.local/state/codex-local-runner/"
    "repository-single-task-runs"
)


@dataclass(frozen=True)
class RepositorySingleTaskRunResult:
    schema_version: str
    run_id: str
    status: str
    reason_code: str
    detail_reason_code: str | None
    repository_id: str
    task_id: str | None
    source_repository_root: str | None
    source_branch: str | None
    source_head_before: str | None
    source_head_after: str | None
    profile_id: str | None
    task_spec_sha256: str | None
    worktree_path: str | None
    worktree_preserved: bool
    task_branch: str | None
    commit_sha: str | None
    commit_parent_sha: str | None
    changed_files: tuple[str, ...]
    adapter_name: str | None
    execution_status: str | None
    validation_status: str | None
    validation_reason: str | None
    retry_attempted: bool
    retry_outcome: str | None
    receipt_path: str | None
    receipt_sha256_path: str | None
    started_at: str
    finished_at: str


class RepositorySingleTaskControllerError(ValueError):
    """Stable, secret-free controller error."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}")


def repository_single_task_run_result_to_mapping(result: RepositorySingleTaskRunResult) -> dict[str, Any]:
    if not isinstance(result, RepositorySingleTaskRunResult):
        raise TypeError("result must be RepositorySingleTaskRunResult")
    value = asdict(result)
    value["changed_files"] = list(result.changed_files)
    return value


def serialize_repository_single_task_run_result(result: RepositorySingleTaskRunResult) -> str:
    return json.dumps(
        repository_single_task_run_result_to_mapping(result),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _git_environment() -> dict[str, str]:
    """Return the minimum environment required for local Git operations."""
    environment = {
        "GIT_TERMINAL_PROMPT": "0",
        "LC_ALL": "C",
        "LANG": "C",
    }
    for name in ("HOME", "PATH", "XDG_CONFIG_HOME"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    return environment


def _git(root: str | Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a bounded local Git command without a shell or credential prompt."""
    return subprocess.run(
        ["git", "-C", os.fspath(root), *arguments],
        shell=False,
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        timeout=20,
        env=_git_environment(),
        check=False,
    )


def _atomic_json(path: Path, value: Any) -> None:
    """Write deterministic JSON atomically and verify the final representation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
        json.loads(path.read_text(encoding="utf-8"))
    finally:
        if temporary.exists():
            temporary.unlink()


def _is_clean(snapshot: Any) -> bool:
    return snapshot.worktree_state == "known_clean" and not any(
        (
            snapshot.tracked_modified_files,
            snapshot.staged_files,
            snapshot.untracked_files,
            snapshot.conflicted_files,
            snapshot.operations_in_progress,
        )
    )


def _worktree_can_be_removed(snapshot: Any, expected_head: str, branch_created: bool, commit_sha: str | None) -> bool:
    return bool(
        snapshot
        and _is_clean(snapshot)
        and snapshot.detached_head
        and snapshot.head_sha == expected_head
        and not branch_created
        and commit_sha is None
    )


def run_repository_single_task(
    repository_id: str,
    task_spec_path: str | os.PathLike[str],
    *,
    registry_path: str | os.PathLike[str] = "config/repos.yaml",
    bindings_path: str | os.PathLike[str] | None = DEFAULT_REPOSITORY_BINDINGS_PATH,
    providers_path: str | os.PathLike[str] = "config/providers.yaml",
    output_root: str | os.PathLike[str] = DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT,
    adapter_resolver: Callable[[], Any] | None = None,
) -> RepositorySingleTaskRunResult:
    """Process exactly one task, returning a receipt-backed terminal result.

    Dependency injection is intentionally limited to the adapter resolver for
    isolated tests; production resolves ``codex_cli`` from the providers file.
    """
    started = _utc_now()
    run_id = "run-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    output_directory = Path(output_root).expanduser() / run_id
    output_directory.mkdir(parents=True, exist_ok=False)

    spec: Any = None
    profile: Any = None
    source_before: Any = None
    source_after: Any = None
    worktree_state: Any = None
    source_root: str | None = None
    source_branch: str | None = None
    source_head: str | None = None
    task_id: str | None = None
    profile_id: str | None = None
    specification_sha: str | None = None
    worktree: Path | None = None
    worktree_preserved = False
    branch_created = False
    task_branch: str | None = None
    commit_sha: str | None = None
    commit_parent: str | None = None
    changed_files: tuple[str, ...] = ()
    adapter_name: str | None = None
    execution_status: str | None = None
    validation_status: str | None = None
    validation_reason: str | None = None
    retry_attempted = False
    retry_outcome: str | None = None
    cleanup_status = "not_started"

    def record(status: str, reason: str, detail: str | None = None) -> RepositorySingleTaskRunResult:
        nonlocal source_after
        try:
            source_after = analyze_repository_state(source_root) if source_root else None
        except (OSError, ValueError):
            source_after = None
        finished = _utc_now()
        receipt_path = output_directory / "receipt.json"
        sha_path = output_directory / "receipt.sha256"
        paths = {
            "receipt": str(receipt_path),
            "receipt_sha256": str(sha_path),
            "pre_source_state": str(output_directory / "pre_source_state.json"),
            "post_source_state": str(output_directory / "post_source_state.json"),
            "worktree_state": str(output_directory / "worktree_state.json"),
            "execution_summary": str(output_directory / "execution_summary.json"),
            "changed_files": str(output_directory / "changed_files.json"),
        }
        receipt = {
            "schema_version": "1", "run_id": run_id, "status": status,
            "reason_code": reason, "detail_reason_code": detail,
            "repository_id": repository_id, "task_id": task_id,
            "task_spec_sha256": specification_sha, "source_repository_root": source_root,
            "profile_id": profile_id,
            "profile_base_branch": getattr(profile, "base_branch", None),
            "profile_max_changed_files": getattr(profile, "max_changed_files", None),
            "approvals": asdict(profile.approval_boundary) if profile is not None else {},
            "source_state_before": repository_state_to_mapping(source_before) if source_before else None,
            "source_state_after": repository_state_to_mapping(source_after) if source_after else None,
            "expected_head_sha": getattr(spec, "expected_head_sha", None),
            "worktree_path": str(worktree) if worktree else None,
            "worktree_preserved": worktree_preserved, "task_branch": task_branch,
            "adapter_name": adapter_name, "execution_status": execution_status,
            "validation_status": validation_status, "validation_reason": validation_reason,
            "retry_attempted": retry_attempted, "retry_outcome": retry_outcome,
            "changed_files": list(changed_files),
            "allowed_changed_paths": list(getattr(spec, "allowed_changed_paths", ())),
            "commit_created": commit_sha is not None, "commit_sha": commit_sha,
            "commit_parent_sha": commit_parent,
            "commit_message": getattr(spec, "commit_message", None),
            "worktree_cleanup_status": cleanup_status, "artifact_paths": paths,
            "started_at": started, "finished_at": finished,
        }
        try:
            _atomic_json(Path(paths["pre_source_state"]), receipt["source_state_before"])
            _atomic_json(Path(paths["post_source_state"]), receipt["source_state_after"])
            _atomic_json(Path(paths["worktree_state"]), {
                "path": str(worktree) if worktree else None,
                "head": getattr(worktree_state, "head_sha", None),
                "branch": getattr(worktree_state, "branch", None),
                "staged_files": list(getattr(worktree_state, "staged_files", ())),
                "operations": list(getattr(worktree_state, "operations_in_progress", ())),
                "changed_files": list(changed_files), "preserved": worktree_preserved,
            })
            _atomic_json(Path(paths["execution_summary"]), {
                "adapter_name": adapter_name, "execution_status": execution_status,
                "validation_status": validation_status, "validation_reason": validation_reason,
                "retry_attempted": retry_attempted, "retry_outcome": retry_outcome,
            })
            _atomic_json(Path(paths["changed_files"]), {
                "allowed_changed_paths": receipt["allowed_changed_paths"],
                "actual_changed_files": list(changed_files),
                "unexpected_changed_files": sorted(set(changed_files) - set(receipt["allowed_changed_paths"])),
                "staged_files": list(getattr(worktree_state, "staged_files", ())),
                "commit_changed_files": list(changed_files) if commit_sha else [],
            })
            if commit_sha:
                paths["commit"] = str(output_directory / "commit.json")
                receipt["artifact_paths"] = paths
                _atomic_json(Path(paths["commit"]), {
                    "commit_sha": commit_sha, "parent_sha": commit_parent,
                    "branch": task_branch, "message": getattr(spec, "commit_message", None),
                    "changed_files": list(changed_files),
                })
            _atomic_json(receipt_path, receipt)
            digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            sha_path.write_text(f"{digest}  receipt.json\n", encoding="utf-8")
            if not json.loads(receipt_path.read_text(encoding="utf-8")):
                raise OSError("receipt readback failed")
        except (OSError, TypeError, ValueError):
            status, reason, detail = "failed", "single_task.receipt.write_failed", None
        return RepositorySingleTaskRunResult(
            "1", run_id, status, reason, detail, repository_id, task_id, source_root,
            source_branch, source_head, getattr(source_after, "head_sha", source_head),
            profile_id, specification_sha, str(worktree) if worktree else None,
            worktree_preserved, task_branch, commit_sha, commit_parent, changed_files,
            adapter_name, execution_status, validation_status, validation_reason,
            retry_attempted, retry_outcome, str(receipt_path), str(sha_path), started, finished,
        )

    try:
        spec = load_repository_single_task_spec(task_spec_path)
        task_id = spec.task_id
        specification_sha = hashlib.sha256(Path(task_spec_path).read_bytes()).hexdigest()
    except (OSError, ValueError):
        return record("blocked", "single_task.task_spec.invalid")
    try:
        registry = load_repository_registry(registry_path, bindings_path)
        resolved = resolve_repository(registry, repository_id)
        profile = resolved.profile
        source_root = profile.repository_root
        profile_id = profile.profile_id
    except (OSError, ValueError):
        return record("blocked", "single_task.repository.resolve_failed")

    for action in ("code_changes", "test_execution", "artifact_generation", "stage", "commit"):
        if getattr(profile.approval_boundary, action) != "automatic":
            return record("blocked", f"single_task.approval.{action}_not_automatic")
    if len(spec.allowed_changed_paths) > profile.max_changed_files:
        return record("blocked", "single_task.scope.allowed_paths_limit_exceeded")
    try:
        source_before = analyze_repository_state(source_root)
    except (OSError, ValueError):
        return record("blocked", "single_task.source.dirty")
    source_branch, source_head = source_before.branch, source_before.head_sha
    if source_before.repository_root != source_root:
        return record("blocked", "single_task.source.repository_root_mismatch")
    if source_before.detached_head:
        return record("blocked", "single_task.source.detached_head")
    if source_branch != profile.base_branch:
        return record("blocked", "single_task.source.branch_mismatch")
    if source_head != spec.expected_head_sha:
        return record("blocked", "single_task.source.head_mismatch")
    if source_before.conflicted_files:
        return record("blocked", "single_task.source.conflicted")
    if source_before.operations_in_progress:
        return record("blocked", "single_task.source.operation_in_progress")
    if not _is_clean(source_before):
        return record("blocked", "single_task.source.dirty")

    task_branch = f"codex-task/{repository_id}/{spec.task_id}"
    if _git(source_root, "show-ref", "--verify", "--quiet", f"refs/heads/{task_branch}").returncode == 0:
        return record("blocked", "single_task.task_branch.exists")
    worktree = output_directory / "worktree"
    try:
        prepared = _git(source_root, "worktree", "add", "--detach", str(worktree), source_head)
    except (OSError, subprocess.TimeoutExpired):
        return record("failed", "single_task.worktree.prepare_failed")
    if prepared.returncode:
        return record("failed", "single_task.worktree.prepare_failed")
    try:
        worktree_state = analyze_repository_state(worktree)
    except (OSError, ValueError):
        worktree_preserved = True
        return record("blocked", "single_task.worktree.initial_state_invalid")
    if not worktree_state.detached_head or worktree_state.head_sha != source_head or not _is_clean(worktree_state):
        worktree_preserved = True
        return record("blocked", "single_task.worktree.initial_state_invalid")
    try:
        bound_profile = bind_repository_profile_to_worktree(profile, worktree)
    except (OSError, ValueError):
        worktree_preserved = True
        return record("blocked", "single_task.profile_binding.failed")
    try:
        if adapter_resolver is not None:
            adapter = adapter_resolver()
        else:
            from orchestrator.config_loader import load_yaml_file
            adapter = resolve_adapter("codex_cli", load_yaml_file(providers_path))
        adapter_name = getattr(adapter, "name", "codex_cli")
    except (OSError, ValueError, TypeError):
        worktree_preserved = True
        return record("blocked", "single_task.provider.resolve_failed")
    if not callable(getattr(adapter, "execute_prepared_worktree", None)):
        worktree_preserved = True
        return record("blocked", "single_task.adapter.prepared_surface_missing")
    try:
        response = adapter.execute_prepared_worktree({
            "prompt": spec.prompt, "worktree_path": str(worktree), "work_dir": str(output_directory),
            "repository_profile": bound_profile,
        })
    except Exception:
        worktree_preserved = True
        return record("failed", "single_task.execution.not_completed")
    if not isinstance(response, dict):
        worktree_preserved = True
        return record("blocked", "single_task.validation.failed")
    execution_status = response.get("status")
    verify = response.get("verify")
    retry_data = response.get("retry")
    if not isinstance(verify, dict) or not isinstance(retry_data, dict):
        worktree_preserved = True
        return record("blocked", "single_task.validation.failed")
    validation_reason = verify.get("reason")
    safe_validation = verify.get("safe_validation")
    validation_status = safe_validation.get("status") if isinstance(safe_validation, dict) else None
    retry_attempted = bool(retry_data.get("attempted"))
    retry_outcome = retry_data.get("outcome")
    if execution_status != "completed":
        worktree_preserved = True
        return record("blocked", "single_task.execution.not_completed")
    if validation_reason == "validation_partial":
        worktree_preserved = True
        return record("blocked", "single_task.validation.partial")
    if validation_reason == "safe_validation_executor_error":
        worktree_preserved = True
        return record("blocked", "single_task.validation.executor_error")
    if not (verify.get("status") == "passed" and validation_reason == "validation_passed" and validation_status == "passed" and retry_outcome in {"not_attempted", "retry_succeeded"}):
        worktree_preserved = True
        return record("blocked", "single_task.validation.failed")

    worktree_state = analyze_repository_state(worktree)
    if worktree_state.head_sha != source_head:
        worktree_preserved = True
        return record("blocked", "single_task.codex.head_changed")
    if not worktree_state.detached_head:
        worktree_preserved = True
        return record("blocked", "single_task.codex.branch_changed")
    if worktree_state.staged_files:
        worktree_preserved = True
        return record("blocked", "single_task.codex.staged_changes")
    if worktree_state.operations_in_progress:
        worktree_preserved = True
        return record("blocked", "single_task.codex.operation_in_progress")
    changed_files = tuple(sorted(set(worktree_state.tracked_modified_files) | set(worktree_state.untracked_files)))
    if not changed_files:
        cleanup = _git(source_root, "worktree", "remove", str(worktree))
        cleanup_status = "removed" if cleanup.returncode == 0 else "failed"
        worktree_preserved = cleanup.returncode != 0
        return record("blocked", "single_task.changed_files.none")
    if len(changed_files) > profile.max_changed_files:
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.limit_exceeded")
    if not set(changed_files).issubset(spec.allowed_changed_paths):
        worktree_preserved = True
        return record("blocked", "single_task.changed_files.out_of_scope")
    root_path = worktree.resolve()
    for changed_path in changed_files:
        candidate = worktree / changed_path
        try:
            if candidate.is_symlink() or not candidate.resolve(strict=False).is_relative_to(root_path):
                worktree_preserved = True
                return record("blocked", "single_task.changed_files.symlink_forbidden")
        except OSError:
            worktree_preserved = True
            return record("blocked", "single_task.changed_files.symlink_forbidden")

    if _git(worktree, "switch", "-c", task_branch).returncode:
        worktree_preserved = True
        return record("blocked", "single_task.branch.create_failed")
    branch_created = True
    if _git(worktree, "add", "--", *changed_files).returncode:
        worktree_preserved = True
        return record("blocked", "single_task.stage.failed")
    worktree_state = analyze_repository_state(worktree)
    if set(worktree_state.staged_files) != set(changed_files) or worktree_state.tracked_modified_files or worktree_state.untracked_files or worktree_state.conflicted_files or worktree_state.operations_in_progress:
        worktree_preserved = True
        return record("blocked", "single_task.stage.state_mismatch")
    if _git(worktree, "commit", "-m", spec.commit_message).returncode:
        worktree_preserved = True
        return record("blocked", "single_task.commit.failed")
    commit_sha = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    commit_parent = _git(worktree, "rev-parse", "HEAD^").stdout.strip()
    subject = _git(worktree, "log", "-1", "--format=%s").stdout.strip()
    committed_files = tuple(sorted(filter(None, _git(worktree, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.splitlines())))
    worktree_state = analyze_repository_state(worktree)
    if len(commit_sha) != 40 or commit_parent != source_head or subject != spec.commit_message or committed_files != changed_files or worktree_state.branch != task_branch or not _is_clean(worktree_state):
        worktree_preserved = True
        return record("failed", "single_task.commit.contract_mismatch")
    source_after = analyze_repository_state(source_root)
    if source_after.branch != profile.base_branch or source_after.head_sha != source_head or not _is_clean(source_after) or source_after.operations_in_progress:
        worktree_preserved = True
        return record("failed", "single_task.source.changed_during_run")
    removed = _git(source_root, "worktree", "remove", str(worktree))
    if removed.returncode:
        worktree_preserved = True
        cleanup_status = "failed"
        return record("failed", "single_task.worktree.cleanup_failed")
    cleanup_status = "removed"
    return record("completed", "single_task.completed")


__all__ = [
    "DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT",
    "RepositorySingleTaskControllerError", "RepositorySingleTaskRunResult",
    "repository_single_task_run_result_to_mapping", "run_repository_single_task",
    "serialize_repository_single_task_run_result",
]

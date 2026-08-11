"""Fail-closed sequential reuse of the repository single-task controller."""
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

from automation.orchestration.repository_multi_cycle_task_spec import load_repository_multi_cycle_task_spec
from automation.orchestration.repository_registry import DEFAULT_REPOSITORY_BINDINGS_PATH, load_repository_registry, resolve_repository
from automation.orchestration.repository_resolved_single_task_controller import (
    DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT, RepositorySingleTaskRunResult, run_repository_single_task,
)
from automation.orchestration.repository_state_analyzer import analyze_repository_state

DEFAULT_REPOSITORY_MULTI_CYCLE_OUTPUT_ROOT = "~/.local/state/codex-local-runner/repository-multi-cycle-runs"


@dataclass(frozen=True)
class RepositoryMultiCycleRunResult:
    schema_version: str
    cycle_run_id: str
    status: str
    reason_code: str
    repository_id: str
    receipt_path: str | None
    receipt_sha256_path: str | None
    source_anchor_sha: str | None
    accepted_head_sha: str | None
    completed_count: int
    stopped_task_id: str | None
    started_at: str
    finished_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            stream.flush(); os.fsync(stream.fileno())
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, path)
        json.loads(path.read_text(encoding="utf-8"))
    finally:
        if temporary.exists():
            temporary.unlink()


def _git(root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", os.fspath(root), *args], stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=20, check=False)


def _receipt_valid(result: RepositorySingleTaskRunResult, *, repository_id: str, task_id: str, source_anchor: str, accepted_head: str, source_root: str) -> bool:
    if not (result.status == "completed" and result.repository_id == repository_id and result.task_id == task_id
            and result.source_head_before == source_anchor and result.source_head_after == source_anchor
            and not result.worktree_preserved and result.commit_sha and result.commit_parent_sha == accepted_head
            and result.receipt_path and result.receipt_sha256_path):
        return False
    commit = result.commit_sha
    if _git(source_root, "cat-file", "-e", f"{commit}^{{commit}}").returncode or _git(source_root, "rev-parse", f"{commit}^").stdout.strip() != accepted_head:
        return False
    if _git(source_root, "merge-base", "--is-ancestor", source_anchor, commit).returncode:
        return False
    try:
        state = analyze_repository_state(source_root)
        receipt_path, sidecar = Path(result.receipt_path), Path(result.receipt_sha256_path)
        receipt_bytes = receipt_path.read_bytes()
        receipt = json.loads(receipt_bytes)
        expected_sidecar = f"{hashlib.sha256(receipt_bytes).hexdigest()}  receipt.json\n"
        if sidecar.read_text(encoding="utf-8") != expected_sidecar:
            return False
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    before = receipt.get("source_state_before") if isinstance(receipt.get("source_state_before"), dict) else {}
    after = receipt.get("source_state_after") if isinstance(receipt.get("source_state_after"), dict) else {}
    return bool(state.head_sha == source_anchor and state.branch and receipt.get("status") == result.status
                and receipt.get("repository_id") == repository_id and receipt.get("task_id") == task_id
                and receipt.get("commit_sha") == commit and receipt.get("commit_parent_sha") == accepted_head
                and before.get("head_sha") == source_anchor and after.get("head_sha") == source_anchor)


def run_repository_multi_cycle(
    repository_id: str, queue_spec_path: str | os.PathLike[str], *,
    registry_path: str | os.PathLike[str] = "config/repos.yaml",
    bindings_path: str | os.PathLike[str] | None = DEFAULT_REPOSITORY_BINDINGS_PATH,
    providers_path: str | os.PathLike[str] = "config/providers.yaml",
    output_root: str | os.PathLike[str] = DEFAULT_REPOSITORY_MULTI_CYCLE_OUTPUT_ROOT,
    single_task_output_root: str | os.PathLike[str] = DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT,
    adapter_resolver: Callable[[], Any] | None = None,
    evaluator_runner: Callable[..., Any] | None = None,
    single_task_runner: Callable[..., RepositorySingleTaskRunResult] = run_repository_single_task,
) -> RepositoryMultiCycleRunResult:
    """Execute an ordered human queue, advancing only receipt-verified commits."""
    started, run_id = _utc_now(), "cycle-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    directory = Path(output_root).expanduser() / run_id
    directory.mkdir(parents=True, exist_ok=False)
    source_anchor = accepted_head = source_root = None
    executed: list[dict[str, Any]] = []
    stopped_task_id = None
    queue_sha = None
    task_count = 0

    def record(status: str, reason: str) -> RepositoryMultiCycleRunResult:
        finished = _utc_now(); receipt_path = directory / "receipt.json"; sha_path = directory / "receipt.sha256"
        receipt = {"schema_version": "1", "cycle_run_id": run_id, "status": status, "reason_code": reason,
                   "repository_id": repository_id, "queue_spec_sha256": queue_sha, "source_anchor_sha": source_anchor,
                   "final_accepted_head_sha": accepted_head, "task_count": task_count, "completed_count": sum(item["status"] == "completed" for item in executed),
                   "stopped_task_id": stopped_task_id, "executed_task_results": executed, "started_at": started, "finished_at": finished}
        try:
            _atomic_json(receipt_path, receipt)
            sha_path.write_text(f"{hashlib.sha256(receipt_path.read_bytes()).hexdigest()}  receipt.json\n", encoding="utf-8")
            json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, TypeError, ValueError):
            status, reason = "failed", "multi_cycle.receipt.write_failed"
        return RepositoryMultiCycleRunResult("1", run_id, status, reason, repository_id, str(receipt_path), str(sha_path), source_anchor, accepted_head, sum(item["status"] == "completed" for item in executed), stopped_task_id, started, finished)

    try:
        queue_bytes = Path(queue_spec_path).read_bytes(); queue_sha = hashlib.sha256(queue_bytes).hexdigest()
        queue = load_repository_multi_cycle_task_spec(queue_spec_path); task_count = len(queue.tasks)
        profile = resolve_repository(load_repository_registry(registry_path, bindings_path), repository_id).profile
        source_root = profile.repository_root
        source = analyze_repository_state(source_root)
        if (source.branch != profile.base_branch or not source.head_sha or source.detached_head or source.conflicted_files
                or source.operations_in_progress or source.tracked_modified_files or source.staged_files or source.untracked_files):
            return record("blocked", "multi_cycle.source.invalid")
        source_anchor = accepted_head = source.head_sha
    except (OSError, ValueError):
        return record("blocked", "multi_cycle.preflight.invalid")

    for task in queue.tasks:
        stopped_task_id = task.task_id
        runtime = directory / f".{task.task_id}.runtime.json"
        try:
            _atomic_json(runtime, {"schema_version": "1", "task_id": task.task_id, "expected_head_sha": source_anchor,
                                   "prompt": task.prompt, "allowed_changed_paths": list(task.allowed_changed_paths), "commit_message": task.commit_message})
            result = single_task_runner(repository_id=repository_id, task_spec_path=str(runtime), registry_path=registry_path,
                                        bindings_path=bindings_path, providers_path=providers_path, output_root=single_task_output_root,
                                        adapter_resolver=adapter_resolver, evaluator_runner=evaluator_runner, execution_base_sha=accepted_head)
        except Exception:
            return record("failed", "multi_cycle.child.invocation_failed")
        finally:
            if runtime.exists():
                runtime.unlink()
        item = {"task_id": task.task_id, "status": getattr(result, "status", "failed"), "reason_code": getattr(result, "reason_code", "multi_cycle.child.invalid"),
                "commit_sha": getattr(result, "commit_sha", None), "parent_sha": getattr(result, "commit_parent_sha", None),
                "worktree_preserved": bool(getattr(result, "worktree_preserved", True)), "child_receipt_path": getattr(result, "receipt_path", None)}
        executed.append(item)
        if result.status == "blocked":
            return record("blocked", "multi_cycle.child.blocked")
        if result.status != "completed":
            return record("failed", "multi_cycle.child.failed")
        if not _receipt_valid(result, repository_id=repository_id, task_id=task.task_id, source_anchor=source_anchor, accepted_head=accepted_head, source_root=source_root):
            return record("failed", "multi_cycle.child.acceptance_invalid")
        accepted_head = result.commit_sha
        stopped_task_id = None
    return record("completed", "multi_cycle.completed")


__all__ = ["DEFAULT_REPOSITORY_MULTI_CYCLE_OUTPUT_ROOT", "RepositoryMultiCycleRunResult", "run_repository_multi_cycle"]

"""Fail-closed sequential reuse of the repository single-task controller."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from automation.orchestration.repository_multi_cycle_task_spec import load_repository_multi_cycle_task_spec
from automation.orchestration.repository_multi_cycle_state import RepositoryMultiCycleStateError, load_latest_checkpoint, write_checkpoint
from automation.orchestration.repository_multi_cycle_status import RepositoryMultiCycleStatusError, read_verified_terminal_receipt
from automation.orchestration.repository_registry import DEFAULT_REPOSITORY_BINDINGS_PATH, load_repository_registry, resolve_repository
from automation.orchestration.repository_resolved_single_task_controller import DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT, RepositorySingleTaskRunResult, run_repository_single_task
from automation.orchestration.repository_single_task_spec import RepositorySingleTaskSpec, serialize_repository_single_task_spec, validate_repository_single_task_spec
from automation.orchestration.repository_state_analyzer import analyze_repository_state

DEFAULT_REPOSITORY_MULTI_CYCLE_OUTPUT_ROOT = "~/.local/state/codex-local-runner/repository-multi-cycle-runs"


@dataclass(frozen=True)
class RepositoryMultiCycleRunResult:
    schema_version: str; cycle_run_id: str; status: str; reason_code: str; repository_id: str
    receipt_path: str | None; receipt_sha256_path: str | None; source_anchor_sha: str | None
    accepted_head_sha: str | None; completed_count: int; stopped_task_id: str | None; started_at: str; finished_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".receipt-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if temporary.exists(): temporary.unlink()


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_bytes(path, _canonical_bytes(value))
    json.loads(path.read_text(encoding="utf-8"))


def _terminal_receipt_mapping(state: Mapping[str, Any]) -> dict[str, Any]:
    completed = state["completed_task_results"]
    public = [{key: item.get(key) for key in ("task_id", "status", "reason_code", "commit_sha", "parent_sha", "worktree_preserved", "child_receipt_path")} for item in completed]
    return {"schema_version":"1","cycle_run_id":state["cycle_run_id"],"status":state["terminal_status"],"reason_code":state["terminal_reason_code"],"repository_id":state["repository_id"],"queue_spec_sha256":state["queue_spec_sha256"],"source_anchor_sha":state["source_anchor_sha"],"continuation_base_sha":state.get("continuation_base_sha",state["source_anchor_sha"]),"final_accepted_head_sha":state["accepted_head_sha"],"task_count":state["task_count"],"completed_count":len(completed),"stopped_task_id":state["stopped_task_id"],"executed_task_results":public,"started_at":state["started_at"],"finished_at":state["terminal_finished_at"]}


def _recover_terminal_pair(directory: Path, state: Mapping[str, Any]) -> tuple[Path, Path]:
    receipt, sidecar = directory / "receipt.json", directory / "receipt.sha256"
    expected_receipt = _canonical_bytes(_terminal_receipt_mapping(state))
    expected_sidecar = f"{hashlib.sha256(expected_receipt).hexdigest()}  receipt.json\n".encode("utf-8")
    has_receipt, has_sidecar = receipt.exists(), sidecar.exists()
    try:
        if has_receipt and receipt.read_bytes() != expected_receipt: raise ValueError("receipt differs")
        if has_sidecar and sidecar.read_bytes() != expected_sidecar: raise ValueError("sidecar differs")
    except OSError as exc:
        raise ValueError("terminal receipt unreadable") from exc
    if not has_receipt: _atomic_bytes(receipt, expected_receipt)
    if not has_sidecar: _atomic_bytes(sidecar, expected_sidecar)
    return receipt, sidecar


def _git(root: str | Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", os.fspath(root), *args], stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=20, check=False)


def _file_sha(path: str | os.PathLike[str] | None) -> str | None:
    return None if path is None else hashlib.sha256(Path(path).expanduser().read_bytes()).hexdigest()


def _child_run_id(cycle_run_id: str, task_index: int, task_id: str) -> str:
    digits = cycle_run_id.removeprefix("cycle-")
    return f"run-{digits}-{task_index:02d}-{hashlib.sha256(task_id.encode('utf-8')).hexdigest()[:16]}"


def _runtime_single_task_spec(task: Any, source_anchor: str) -> tuple[RepositorySingleTaskSpec, str]:
    spec = validate_repository_single_task_spec(RepositorySingleTaskSpec("1", task.task_id, source_anchor, task.prompt, tuple(task.allowed_changed_paths), task.commit_message, task.execution_timeout_seconds, task.validation_timeout_seconds, task.completion_evaluator_timeout_seconds, task.completion_rework_timeout_seconds))
    return spec, hashlib.sha256(serialize_repository_single_task_spec(spec).encode("utf-8")).hexdigest()


def _clean_source(root: str, branch: str, anchor: str) -> bool:
    try: state = analyze_repository_state(root)
    except (OSError, ValueError): return False
    return bool(state.repository_root == root and state.branch == branch and state.head_sha == anchor and not state.detached_head and not state.conflicted_files and not state.operations_in_progress and not state.tracked_modified_files and not state.staged_files and not state.untracked_files)


def _load_verified_child_receipt(*, receipt_path: Path, expected_run_id: str, repository_id: str, task_id: str, task_spec_sha256: str, source_root: str, source_branch: str, source_anchor: str, expected_parent: str, expected_status: str | None = None) -> Mapping[str, Any] | None:
    sidecar = receipt_path.with_name("receipt.sha256")
    try:
        payload = receipt_path.read_bytes(); receipt = json.loads(payload); expected = f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"
        if not isinstance(receipt, dict) or sidecar.read_text(encoding="utf-8") != expected: return None
    except (OSError, ValueError, json.JSONDecodeError): return None
    before, after = receipt.get("source_state_before"), receipt.get("source_state_after")
    commit = receipt.get("commit_sha")
    status = receipt.get("status")
    if not (receipt.get("schema_version") == "1" and receipt.get("run_id") == expected_run_id and receipt.get("repository_id") == repository_id and receipt.get("task_id") == task_id and receipt.get("task_spec_sha256") == task_spec_sha256 and receipt.get("source_repository_root") == source_root and status in {"completed", "blocked", "failed"} and (expected_status is None or status == expected_status) and isinstance(receipt.get("reason_code"), str) and bool(receipt.get("reason_code")) and isinstance(before, dict) and isinstance(after, dict) and before.get("head_sha") == source_anchor and after.get("head_sha") == source_anchor and _clean_source(source_root, source_branch, source_anchor)): return None
    if status == "completed":
        if not (receipt.get("worktree_preserved") is False and receipt.get("commit_created") is True and isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) and receipt.get("commit_parent_sha") == expected_parent): return None
        if _git(source_root, "cat-file", "-e", f"{commit}^{{commit}}").returncode or _git(source_root, "rev-parse", f"{commit}^").stdout.strip() != expected_parent or _git(source_root, "merge-base", "--is-ancestor", source_anchor, commit).returncode: return None
    elif status == "blocked":
        if receipt.get("commit_created") is not False or commit is not None or receipt.get("commit_parent_sha") is not None: return None
    elif receipt.get("commit_created") is False:
        if commit is not None or receipt.get("commit_parent_sha") is not None: return None
    else:
        if not (receipt.get("commit_created") is True and isinstance(commit, str) and re.fullmatch(r"[0-9a-f]{40}", commit) and receipt.get("commit_parent_sha") == expected_parent and _git(source_root, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0 and _git(source_root, "rev-parse", f"{commit}^").stdout.strip() == expected_parent and _git(source_root, "merge-base", "--is-ancestor", source_anchor, commit).returncode == 0): return None
    return receipt


def _load_verified_completed_child_receipt(**kwargs: Any) -> Mapping[str, Any] | None:
    return _load_verified_child_receipt(**kwargs, expected_status="completed")


def _receipt_valid(result: RepositorySingleTaskRunResult, *, repository_id: str, task_id: str, task_spec_sha256: str, source_anchor: str, accepted_head: str, source_root: str, source_branch: str) -> bool:
    if not (result.status == "completed" and result.run_id and result.repository_id == repository_id and result.task_id == task_id and result.task_spec_sha256 == task_spec_sha256 and result.commit_sha and result.commit_parent_sha == accepted_head and result.receipt_path and result.receipt_sha256_path and result.source_head_before == source_anchor and result.source_head_after == source_anchor and not result.worktree_preserved): return False
    receipt = _load_verified_completed_child_receipt(receipt_path=Path(result.receipt_path), expected_run_id=result.run_id, repository_id=repository_id, task_id=task_id, task_spec_sha256=task_spec_sha256, source_root=source_root, source_branch=source_branch, source_anchor=source_anchor, expected_parent=accepted_head)
    return bool(receipt and receipt.get("commit_sha") == result.commit_sha and Path(result.receipt_sha256_path) == Path(result.receipt_path).with_name("receipt.sha256"))


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) is not None


def _verified_continuation_edge(receipt: Mapping[str, Any], *, source_root: str, source_anchor: str) -> tuple[str, str] | None:
    """Validate one terminal receipt's completed prefix against local Git."""
    if receipt.get("source_anchor_sha") != source_anchor:
        return None
    completed_count, results, final = receipt.get("completed_count"), receipt.get("executed_task_results"), receipt.get("final_accepted_head_sha")
    if not isinstance(completed_count, int) or not isinstance(results, list) or len(results) != completed_count or not _sha(final):
        raise ValueError("multi_cycle.continuation.evidence_invalid")
    if completed_count == 0:
        # A terminal attempt may start at a previously verified continuation
        # tip and fail before accepting another queue task.  It creates no new
        # edge; the discovery pass verifies that its base is already reachable.
        base = receipt.get("continuation_base_sha", source_anchor)
        if not _sha(base) or final != base or results:
            raise ValueError("multi_cycle.continuation.evidence_invalid")
        try:
            valid = (
                _git(source_root, "cat-file", "-e", f"{base}^{{commit}}").returncode == 0
                and _git(source_root, "merge-base", "--is-ancestor", source_anchor, base).returncode == 0
            )
        except (OSError, subprocess.TimeoutExpired):
            valid = False
        if not valid:
            raise ValueError("multi_cycle.continuation.evidence_invalid")
        return None
    first = results[0] if results else None
    if not isinstance(first, Mapping) or not _sha(first.get("parent_sha")):
        raise ValueError("multi_cycle.continuation.evidence_invalid")
    base = receipt.get("continuation_base_sha", first["parent_sha"])
    if not _sha(base) or first["parent_sha"] != base:
        raise ValueError("multi_cycle.continuation.evidence_invalid")
    parent = base
    for item in results:
        if not isinstance(item, Mapping) or item.get("status") != "completed" or not _sha(item.get("commit_sha")) or item.get("parent_sha") != parent:
            raise ValueError("multi_cycle.continuation.evidence_invalid")
        commit = item["commit_sha"]
        try:
            exists = _git(source_root, "cat-file", "-e", f"{commit}^{{commit}}").returncode == 0
            actual_parent = _git(source_root, "rev-parse", f"{commit}^").stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            exists, actual_parent = False, ""
        if not exists or actual_parent != parent:
            raise ValueError("multi_cycle.continuation.git_parent_invalid")
        parent = commit
    try:
        anchor_to_base = _git(source_root, "merge-base", "--is-ancestor", source_anchor, base).returncode == 0
        base_to_final = _git(source_root, "merge-base", "--is-ancestor", base, final).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        anchor_to_base = base_to_final = False
    if parent != final or not anchor_to_base or not base_to_final:
        raise ValueError("multi_cycle.continuation.evidence_invalid")
    return base, final


def _terminal_zero_completion_noop_is_verified(directory: Path, receipt: Mapping[str, Any], *, repository_id: str, source_root: str, source_anchor: str, reachable_heads: set[str]) -> bool:
    """Check that a zero-completion terminal is a no-op, not forged progress."""
    base = receipt.get("continuation_base_sha")
    if not (_sha(base) and receipt.get("final_accepted_head_sha") == base and base in reachable_heads):
        return False
    try:
        state, _ = load_latest_checkpoint(directory / "state")
    except (OSError, RepositoryMultiCycleStateError):
        return False
    terminal = state.get("terminal_task_result")
    child_valid = False
    if isinstance(terminal, dict):
        try:
            child_path = Path(str(terminal.get("child_receipt_path", "")))
            payload = child_path.read_bytes()
            child = json.loads(payload)
            sidecar = child_path.with_name("receipt.sha256").read_text(encoding="utf-8")
            child_valid = (
                child_path.name == "receipt.json"
                and terminal.get("child_receipt_sha256") == hashlib.sha256(payload).hexdigest()
                and sidecar == f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n"
                and isinstance(child, dict)
                and child.get("repository_id") == repository_id
                and child.get("task_id") == terminal.get("task_id")
                and child.get("status") == terminal.get("status")
                and child.get("commit_created") is False
                and child.get("commit_sha") is None
                and child.get("commit_parent_sha") is None
            )
        except (OSError, ValueError, json.JSONDecodeError):
            child_valid = False
    valid = (
        state.get("cycle_run_id") == directory.name == receipt.get("cycle_run_id")
        and state.get("repository_id") == receipt.get("repository_id") == repository_id
        and state.get("queue_spec_sha256") == receipt.get("queue_spec_sha256")
        and state.get("source_repository_root") == source_root
        and state.get("source_anchor_sha") == receipt.get("source_anchor_sha") == source_anchor
        and state.get("continuation_base_sha") == base
        and state.get("accepted_head_sha") == base
        and state.get("next_task_index") == 0
        and state.get("completed_task_results") == []
        and state.get("lifecycle_status") == "finalizing"
        and state.get("terminal_status") == receipt.get("status") in {"blocked", "failed"}
        and state.get("terminal_reason_code") == receipt.get("reason_code")
        and state.get("stopped_task_id") == receipt.get("stopped_task_id")
        and isinstance(terminal, dict)
        and terminal.get("task_index") == 0
        and terminal.get("task_id") == receipt.get("stopped_task_id")
        and terminal.get("status") == receipt.get("status")
        and terminal.get("commit_created") is False
        and terminal.get("commit_sha") is None
        and terminal.get("commit_parent_sha") is None
        and child_valid
    )
    return bool(valid)


def _discover_verified_continuation_base(repository_id: str, source_root: str, source_anchor: str, cycle_output_root: str | os.PathLike[str], *, exclude_cycle_run_id: str | None = None) -> str:
    """Follow only uniquely verified terminal accepted-chain edges from anchor."""
    root = Path(cycle_output_root).expanduser()
    edges: dict[str, set[str]] = {}
    zero_completion: list[tuple[Path, Mapping[str, Any]]] = []
    if not root.exists():
        return source_anchor
    try:
        directories = sorted((item for item in root.iterdir() if item.is_dir() and item.name.startswith("cycle-")), key=lambda item: item.name)
    except OSError as exc:
        raise ValueError("multi_cycle.continuation.discovery_invalid") from exc
    for directory in directories:
        if directory.name == exclude_cycle_run_id:
            continue
        receipt_path = directory / "receipt.json"
        if not receipt_path.exists():
            continue
        try:
            raw = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict) or raw.get("repository_id") != repository_id or raw.get("source_anchor_sha") != source_anchor:
            continue
        try:
            receipt = read_verified_terminal_receipt(directory, repository_id, None)
        except RepositoryMultiCycleStatusError as exc:
            raise ValueError("multi_cycle.continuation.evidence_invalid") from exc
        if receipt is None:
            continue
        edge = _verified_continuation_edge(receipt, source_root=source_root, source_anchor=source_anchor)
        if edge is not None:
            edges.setdefault(edge[0], set()).add(edge[1])
        elif receipt.get("completed_count") == 0:
            zero_completion.append((directory, receipt))
    tip, seen = source_anchor, {source_anchor}
    while tip in edges:
        targets = edges[tip]
        if len(targets) == 1:
            selected = next(iter(targets))
        else:
            # Terminal-resume receipts carry a cumulative verified prefix.
            # Consequently A→B and a later A→C (where B is an ancestor of C)
            # are equivalent observations, not a fork.  Only a unique deepest
            # descendant is safe; sibling targets remain ambiguous.
            deepest = []
            for candidate in targets:
                try:
                    if all(_git(source_root, "merge-base", "--is-ancestor", other, candidate).returncode == 0 for other in targets):
                        deepest.append(candidate)
                except (OSError, subprocess.TimeoutExpired):
                    pass
            if len(deepest) != 1:
                raise ValueError("multi_cycle.continuation.ambiguous")
            selected = deepest[0]
        tip = selected
        if tip in seen:
            raise ValueError("multi_cycle.continuation.evidence_invalid")
        seen.add(tip)
    # A zero-new-completion terminal must prove that it began at an already
    # verified accepted tip.  It contributes no edge and therefore cannot
    # replace or poison that prior evidence.
    for directory, receipt in zero_completion:
        if not _terminal_zero_completion_noop_is_verified(
            directory, receipt, repository_id=repository_id, source_root=source_root,
            source_anchor=source_anchor, reachable_heads=seen,
        ):
            raise ValueError("multi_cycle.continuation.evidence_invalid")
    return tip


def _load_verified_terminal_resume_seed(*, predecessor_cycle_run_id: str, repository_id: str, queue_sha256: str, queue: Any, source_root: str, source_branch: str, source_anchor: str, cycle_output_root: Path, single_task_output_root: Path) -> tuple[str, str, list[dict[str, Any]]]:
    """Return a verified contiguous accepted prefix from one terminal cycle."""
    if not isinstance(predecessor_cycle_run_id, str) or not re.fullmatch(r"cycle-[0-9]{20}", predecessor_cycle_run_id):
        raise ValueError("multi_cycle.terminal_resume.run_id.invalid")
    directory = cycle_output_root / predecessor_cycle_run_id
    try:
        receipt = read_verified_terminal_receipt(directory, repository_id, queue_sha256)
        state, _ = load_latest_checkpoint(directory / "state")
    except (OSError, RepositoryMultiCycleStatusError, RepositoryMultiCycleStateError) as exc:
        raise ValueError("multi_cycle.terminal_resume.evidence_invalid") from exc
    if receipt is None or receipt.get("status") == "completed":
        raise ValueError("multi_cycle.terminal_resume.not_resumable")
    completed = receipt.get("executed_task_results")
    count = receipt.get("completed_count")
    base, accepted = receipt.get("continuation_base_sha"), receipt.get("final_accepted_head_sha")
    if not (
        receipt.get("cycle_run_id") == predecessor_cycle_run_id
        and receipt.get("repository_id") == repository_id
        and receipt.get("queue_spec_sha256") == queue_sha256
        and receipt.get("source_anchor_sha") == source_anchor
        and isinstance(count, int) and not isinstance(count, bool) and 0 <= count < len(queue.tasks)
        and isinstance(completed, list) and len(completed) == count
        and _sha(base) and _sha(accepted)
        and receipt.get("stopped_task_id") == queue.tasks[count].task_id
        and state.get("cycle_run_id") == predecessor_cycle_run_id
        and state.get("repository_id") == repository_id
        and state.get("queue_spec_sha256") == queue_sha256
        and state.get("source_repository_root") == source_root
        and state.get("source_anchor_sha") == source_anchor
        and state.get("continuation_base_sha") == base
        and state.get("accepted_head_sha") == accepted
        and state.get("next_task_index") == count
        and state.get("completed_task_results") == completed
        and state.get("lifecycle_status") == "finalizing"
        and state.get("terminal_status") == receipt.get("status")
        and state.get("terminal_reason_code") == receipt.get("reason_code")
        and state.get("stopped_task_id") == receipt.get("stopped_task_id")
        and isinstance(state.get("terminal_task_result"), dict)
    ):
        raise ValueError("multi_cycle.terminal_resume.evidence_invalid")
    parent = base
    seeded: list[dict[str, Any]] = []
    for index, item in enumerate(completed):
        task = queue.tasks[index]
        spec, spec_sha = _runtime_single_task_spec(task, source_anchor)
        if not isinstance(item, Mapping) or item.get("task_id") != task.task_id or item.get("status") != "completed" or item.get("parent_sha") != parent or not _sha(item.get("commit_sha")):
            raise ValueError("multi_cycle.terminal_resume.prefix_invalid")
        receipt_path = Path(str(item.get("child_receipt_path", "")))
        try:
            if receipt_path.name != "receipt.json" or not receipt_path.is_relative_to(single_task_output_root):
                raise ValueError
        except ValueError as exc:
            raise ValueError("multi_cycle.terminal_resume.prefix_invalid") from exc
        child_id = receipt_path.parent.name
        verified = _load_verified_completed_child_receipt(
            receipt_path=receipt_path, expected_run_id=child_id, repository_id=repository_id,
            task_id=task.task_id, task_spec_sha256=spec_sha, source_root=source_root,
            source_branch=source_branch, source_anchor=source_anchor, expected_parent=parent,
        )
        if not verified or verified.get("commit_sha") != item.get("commit_sha"):
            raise ValueError("multi_cycle.terminal_resume.prefix_invalid")
        seeded.append(dict(item)); parent = item["commit_sha"]
    terminal = state["terminal_task_result"]
    task = queue.tasks[count]; spec, spec_sha = _runtime_single_task_spec(task, source_anchor)
    child_id = _child_run_id(predecessor_cycle_run_id, count, task.task_id)
    child_path = single_task_output_root / child_id / "receipt.json"
    terminal_receipt = _load_verified_child_receipt(
        receipt_path=child_path, expected_run_id=child_id, repository_id=repository_id,
        task_id=task.task_id, task_spec_sha256=spec_sha, source_root=source_root,
        source_branch=source_branch, source_anchor=source_anchor, expected_parent=parent,
        expected_status=receipt["status"],
    )
    if not (
        terminal_receipt and terminal.get("task_index") == count and terminal.get("task_id") == task.task_id
        and terminal.get("status") == receipt["status"] and terminal.get("child_run_id") == child_id
        and terminal.get("task_spec_sha256") == spec_sha and terminal.get("child_receipt_path") == str(child_path)
        and terminal.get("commit_created") is False and terminal.get("commit_sha") is None
        and terminal.get("commit_parent_sha") is None and parent == accepted
    ):
        raise ValueError("multi_cycle.terminal_resume.evidence_invalid")
    return base, accepted, seeded


def run_repository_multi_cycle(repository_id: str, queue_spec_path: str | os.PathLike[str], *, registry_path: str | os.PathLike[str] = "config/repos.yaml", bindings_path: str | os.PathLike[str] | None = DEFAULT_REPOSITORY_BINDINGS_PATH, providers_path: str | os.PathLike[str] = "config/providers.yaml", output_root: str | os.PathLike[str] = DEFAULT_REPOSITORY_MULTI_CYCLE_OUTPUT_ROOT, single_task_output_root: str | os.PathLike[str] = DEFAULT_REPOSITORY_SINGLE_TASK_OUTPUT_ROOT, adapter_resolver: Callable[[], Any] | None = None, evaluator_runner: Callable[..., Any] | None = None, single_task_runner: Callable[..., RepositorySingleTaskRunResult] = run_repository_single_task, resume_cycle_run_id: str | None = None, terminal_resume_cycle_run_id: str | None = None) -> RepositoryMultiCycleRunResult:
    """Execute or resume an ordered queue; only verified receipts advance it."""
    started = _utc_now(); generated = "cycle-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    root = Path(output_root).expanduser()
    if resume_cycle_run_id is not None and terminal_resume_cycle_run_id is not None:
        raise ValueError("multi_cycle.resume.mode_conflict")
    if resume_cycle_run_id is not None:
        if not isinstance(resume_cycle_run_id, str) or not re.fullmatch(r"cycle-[0-9]{20}", resume_cycle_run_id): raise ValueError("multi_cycle.resume.run_id.invalid")
        run_id, directory = resume_cycle_run_id, root / resume_cycle_run_id
        if not directory.is_dir() or directory.parent != root: raise ValueError("multi_cycle.resume.run_not_found")
    else:
        run_id, directory = generated, root / generated; directory.mkdir(parents=True, exist_ok=False)
    queue_sha = registry_sha = bindings_sha = providers_sha = source_root = source_anchor = continuation_base = accepted_head = None
    source_branch = None; task_count = 0; completed: list[dict[str, Any]] = []; stopped_task_id: str | None = None

    def record(status: str, reason: str) -> RepositoryMultiCycleRunResult:
        finished = _utc_now(); path, sidecar = directory / "receipt.json", directory / "receipt.sha256"
        public = [{key: item.get(key) for key in ("task_id", "status", "reason_code", "commit_sha", "parent_sha", "worktree_preserved", "child_receipt_path")} for item in completed]
        receipt = {"schema_version":"1","cycle_run_id":run_id,"status":status,"reason_code":reason,"repository_id":repository_id,"queue_spec_sha256":queue_sha,"source_anchor_sha":source_anchor,"continuation_base_sha":continuation_base,"final_accepted_head_sha":accepted_head,"task_count":task_count,"completed_count":len(completed),"stopped_task_id":stopped_task_id,"executed_task_results":public,"started_at":started,"finished_at":finished}
        try:
            _atomic_json(path, receipt); sidecar.write_text(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  receipt.json\n", encoding="utf-8")
        except (OSError, TypeError, ValueError): status, reason = "failed", "multi_cycle.receipt.write_failed"
        return RepositoryMultiCycleRunResult("1", run_id, status, reason, repository_id, str(path), str(sidecar), source_anchor, accepted_head, len(completed), stopped_task_id, started, finished)

    try:
        queue_path = Path(queue_spec_path).expanduser(); queue_sha = _file_sha(queue_path); registry_sha = _file_sha(registry_path); bindings_sha = _file_sha(bindings_path); providers_sha = _file_sha(providers_path)
        queue = load_repository_multi_cycle_task_spec(queue_path); task_count = len(queue.tasks)
        profile = resolve_repository(load_repository_registry(registry_path, bindings_path), repository_id).profile
        source_root, source_branch = profile.repository_root, profile.base_branch
        source = analyze_repository_state(source_root)
        if not _clean_source(source_root, source_branch, source.head_sha or ""): return record("blocked", "multi_cycle.source.invalid")
        source_anchor = source.head_sha
        if resume_cycle_run_id is None:
            continuation_base = source_anchor
            try: continuation_base = _discover_verified_continuation_base(repository_id, source_root, source_anchor, root, exclude_cycle_run_id=run_id)
            except ValueError as exc: return record("blocked", str(exc))
            if terminal_resume_cycle_run_id is not None:
                continuation_base, accepted_head, completed = _load_verified_terminal_resume_seed(
                    predecessor_cycle_run_id=terminal_resume_cycle_run_id, repository_id=repository_id,
                    queue_sha256=queue_sha, queue=queue, source_root=source_root,
                    source_branch=source_branch, source_anchor=source_anchor,
                    cycle_output_root=root, single_task_output_root=Path(single_task_output_root).expanduser(),
                )
        else:
            continuation_base = source_anchor
        if accepted_head is None:
            accepted_head = continuation_base
    except (OSError, ValueError): return record("blocked", "multi_cycle.preflight.invalid")

    terminal_resume_start_index = len(completed) if terminal_resume_cycle_run_id is not None else None

    def checkpoint(lifecycle: str, active: dict[str, Any] | None = None, *, terminal_status: str | None = None, terminal_reason_code: str | None = None, terminal_finished_at: str | None = None, stopped_task: str | None = None, terminal_task_result: dict[str, Any] | None = None) -> None:
        state = {"cycle_run_id":run_id,"repository_id":repository_id,"queue_spec_sha256":queue_sha,"registry_sha256":registry_sha,"bindings_sha256":bindings_sha,"providers_sha256":providers_sha,"source_repository_root":source_root,"source_anchor_sha":source_anchor,"continuation_base_sha":continuation_base,"accepted_head_sha":accepted_head,"task_count":task_count,"next_task_index":len(completed),"completed_task_results":completed,"active_task":active,"terminal_task_result":terminal_task_result,"lifecycle_status":lifecycle,"terminal_status":terminal_status,"terminal_reason_code":terminal_reason_code,"terminal_finished_at":terminal_finished_at,"stopped_task_id":stopped_task,"started_at":started,"updated_at":_utc_now()}
        if terminal_resume_cycle_run_id is not None:
            state.update({"terminal_resume_requested":True,"terminal_resume_predecessor_cycle_run_id":terminal_resume_cycle_run_id,"terminal_resume_task_index":terminal_resume_start_index,"terminal_resume_accepted_head_sha":continuation_base if terminal_resume_start_index == 0 else completed[terminal_resume_start_index - 1]["commit_sha"],"terminal_resume_accepted_task_ids":[item["task_id"] for item in completed[:terminal_resume_start_index]]})
        write_checkpoint(directory / "state", state)

    def terminalize(status: str, reason: str, task: Any, index: int, child_id: str, spec_sha: str, receipt: Mapping[str, Any]) -> RepositoryMultiCycleRunResult:
        nonlocal stopped_task_id
        stopped_task_id = task.task_id; finished = _utc_now(); child_path = Path(str(receipt.get("artifact_paths", {}).get("receipt", "")))
        # The receipt path is deterministic and never carries prompt material.
        child_path = Path(single_task_output_root).expanduser() / child_id / "receipt.json"
        terminal_child = {"task_index":index,"task_id":task.task_id,"status":status,"reason_code":receipt.get("reason_code"),"child_run_id":child_id,"task_spec_sha256":spec_sha,"child_receipt_path":str(child_path),"child_receipt_sha256":hashlib.sha256(child_path.read_bytes()).hexdigest(),"worktree_preserved":receipt.get("worktree_preserved"),"commit_created":receipt.get("commit_created"),"commit_sha":receipt.get("commit_sha"),"commit_parent_sha":receipt.get("commit_parent_sha")}
        checkpoint("finalizing", terminal_status=status, terminal_reason_code=reason, terminal_finished_at=finished, stopped_task=task.task_id, terminal_task_result=terminal_child)
        state, _ = load_latest_checkpoint(directory / "state")
        try: receipt_path, sidecar_path = _recover_terminal_pair(directory, state)
        except (OSError, ValueError): return RepositoryMultiCycleRunResult("1", run_id, "failed", "multi_cycle.receipt.write_failed", repository_id, str(directory / "receipt.json"), str(directory / "receipt.sha256"), source_anchor, accepted_head, len(completed), stopped_task_id, started, finished)
        return RepositoryMultiCycleRunResult("1", run_id, status, reason, repository_id, str(receipt_path), str(sidecar_path), source_anchor, accepted_head, len(completed), stopped_task_id, started, finished)

    if resume_cycle_run_id is None:
        checkpoint("initialized")
    else:
        try:
            state, _ = load_latest_checkpoint(directory / "state"); started = state.get("started_at", started)
            for key, value, reason in (("repository_id",repository_id,"multi_cycle.resume.repository_mismatch"),("queue_spec_sha256",queue_sha,"multi_cycle.resume.queue_mismatch"),("registry_sha256",registry_sha,"multi_cycle.resume.registry_mismatch"),("bindings_sha256",bindings_sha,"multi_cycle.resume.bindings_mismatch"),("providers_sha256",providers_sha,"multi_cycle.resume.providers_mismatch"),("source_repository_root",source_root,"multi_cycle.resume.repository_root_mismatch"),("source_anchor_sha",source_anchor,"multi_cycle.resume.source_anchor_mismatch")):
                if state.get(key) != value: return record("blocked", reason)
            continuation_base = state.get("continuation_base_sha", source_anchor)
            try: rediscovered = _discover_verified_continuation_base(repository_id, source_root, source_anchor, root, exclude_cycle_run_id=run_id)
            except ValueError: return record("blocked", "multi_cycle.resume.continuation_discovery_invalid")
            if continuation_base != rediscovered: return record("blocked", "multi_cycle.resume.continuation_base_mismatch")
            completed = list(state.get("completed_task_results", [])); accepted_head = state.get("accepted_head_sha")
            if not isinstance(accepted_head, str) or len(completed) != state.get("next_task_index") or len(completed) > task_count: return record("blocked", "multi_cycle.resume.accepted_chain_invalid")
            parent = continuation_base
            for index, item in enumerate(completed):
                task = queue.tasks[index]; spec, spec_sha = _runtime_single_task_spec(task, source_anchor); child_id = _child_run_id(run_id, index, task.task_id); child_dir = Path(single_task_output_root).expanduser() / child_id
                receipt = _load_verified_completed_child_receipt(receipt_path=child_dir / "receipt.json", expected_run_id=child_id, repository_id=repository_id, task_id=task.task_id, task_spec_sha256=spec_sha, source_root=source_root, source_branch=source_branch, source_anchor=source_anchor, expected_parent=parent)
                if not receipt or item.get("commit_sha") != receipt.get("commit_sha"): return record("blocked", "multi_cycle.resume.accepted_chain_invalid")
                parent = receipt["commit_sha"]
            if parent != accepted_head: return record("blocked", "multi_cycle.resume.accepted_chain_invalid")
            if state.get("lifecycle_status") == "finalizing":
                terminal_status, terminal_reason = state.get("terminal_status"), state.get("terminal_reason_code")
                terminal_child_invalid = False
                valid_finalizing = (state.get("active_task") is None and isinstance(state.get("terminal_finished_at"), str) and bool(state.get("terminal_finished_at")) and state.get("next_task_index") == len(completed) and ((terminal_status == "completed" and terminal_reason == "multi_cycle.completed" and state.get("stopped_task_id") is None and state.get("terminal_task_result") is None and len(completed) == task_count) or (terminal_status in {"blocked", "failed"} and terminal_reason == f"multi_cycle.child.{terminal_status}" and isinstance(state.get("stopped_task_id"), str) and len(completed) < task_count and isinstance(state.get("terminal_task_result"), dict))))
                if valid_finalizing and terminal_status in {"blocked", "failed"}:
                    index = len(completed); task = queue.tasks[index]; spec, spec_sha = _runtime_single_task_spec(task, source_anchor); child_id = _child_run_id(run_id, index, task.task_id); child_path = Path(single_task_output_root).expanduser() / child_id / "receipt.json"; terminal = state["terminal_task_result"]
                    verified = _load_verified_child_receipt(receipt_path=child_path, expected_run_id=child_id, repository_id=repository_id, task_id=task.task_id, task_spec_sha256=spec_sha, source_root=source_root, source_branch=source_branch, source_anchor=source_anchor, expected_parent=accepted_head, expected_status=terminal_status)
                    valid_finalizing = bool(verified and terminal.get("task_index") == index and terminal.get("task_id") == task.task_id and terminal.get("status") == terminal_status and terminal.get("child_run_id") == child_id and terminal.get("task_spec_sha256") == spec_sha and terminal.get("child_receipt_path") == str(child_path)); terminal_child_invalid = not valid_finalizing
                if not valid_finalizing:
                    return RepositoryMultiCycleRunResult("1", run_id, "failed", "multi_cycle.resume.terminal_child_invalid" if terminal_child_invalid else "multi_cycle.resume.finalizing_state_invalid", repository_id, str(directory / "receipt.json"), str(directory / "receipt.sha256"), source_anchor, accepted_head, len(completed), None, started, _utc_now())
                try:
                    receipt_path, sidecar_path = _recover_terminal_pair(directory, state)
                except (OSError, ValueError):
                    return RepositoryMultiCycleRunResult("1", run_id, "failed", "multi_cycle.resume.terminal_receipt_invalid", repository_id, str(directory / "receipt.json"), str(directory / "receipt.sha256"), source_anchor, accepted_head, len(completed), None, started, state["terminal_finished_at"])
                return RepositoryMultiCycleRunResult("1", run_id, terminal_status, terminal_reason, repository_id, str(receipt_path), str(sidecar_path), source_anchor, accepted_head, len(completed), state.get("stopped_task_id"), started, state["terminal_finished_at"])
            active = state.get("active_task")
            if active:
                index = len(completed)
                if index >= task_count: return record("blocked", "multi_cycle.resume.active_task_mismatch")
                task = queue.tasks[index]; spec, spec_sha = _runtime_single_task_spec(task, source_anchor); child_id = _child_run_id(run_id, index, task.task_id); child_dir = Path(single_task_output_root).expanduser() / child_id
                expected_active = {"task_index":index,"task_id":task.task_id,"expected_parent_sha":accepted_head,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir / "receipt.json"),"task_spec_sha256":spec_sha}
                if any(active.get(key) != value for key,value in expected_active.items()): return record("blocked", "multi_cycle.resume.active_task_mismatch")
                if child_dir.exists():
                    receipt = _load_verified_child_receipt(receipt_path=child_dir / "receipt.json", expected_run_id=child_id, repository_id=repository_id, task_id=task.task_id, task_spec_sha256=spec_sha, source_root=source_root, source_branch=source_branch, source_anchor=source_anchor, expected_parent=accepted_head)
                    if receipt is None:
                        receipt_path = child_dir / "receipt.json"
                        if receipt_path.is_file(): return record("failed", "multi_cycle.child.acceptance_invalid")
                        return record("blocked", "multi_cycle.resume.child_incomplete")
                    if receipt["status"] in {"blocked", "failed"}: return terminalize(receipt["status"], f"multi_cycle.child.{receipt['status']}", task, index, child_id, spec_sha, receipt)
                    completed.append({"task_id":task.task_id,"status":"completed","reason_code":receipt.get("reason_code"),"commit_sha":receipt["commit_sha"],"parent_sha":receipt["commit_parent_sha"],"worktree_preserved":False,"child_receipt_path":str(child_dir / "receipt.json")})
                    accepted_head = receipt["commit_sha"]; checkpoint("accepted_task"); active = None
        except (OSError, ValueError, RepositoryMultiCycleStateError): return record("blocked", "multi_cycle.resume.state_invalid")

    for index in range(len(completed), task_count):
        task = queue.tasks[index]; stopped_task_id = task.task_id; spec, spec_sha = _runtime_single_task_spec(task, source_anchor); child_id = _child_run_id(run_id, index, task.task_id); child_dir = Path(single_task_output_root).expanduser() / child_id
        # A resumed active state has already been durably written; do not duplicate it.
        if not (resume_cycle_run_id is not None and index == len(completed) and 'active' in locals() and active):
            checkpoint("active_task", {"task_index":index,"task_id":task.task_id,"expected_parent_sha":accepted_head,"child_run_id":child_id,"child_output_directory":str(child_dir),"child_receipt_path":str(child_dir / "receipt.json"),"task_spec_sha256":spec_sha})
        try:
            result = single_task_runner(repository_id=repository_id, task_spec_path=None, task_spec_override=spec, registry_path=registry_path, bindings_path=bindings_path, providers_path=providers_path, output_root=single_task_output_root, adapter_resolver=adapter_resolver, evaluator_runner=evaluator_runner, execution_base_sha=accepted_head, requested_run_id=child_id)
        except Exception: return record("failed", "multi_cycle.child.invocation_failed")
        if result.status in {"blocked", "failed"}:
            if not (result.run_id == child_id and result.repository_id == repository_id and result.task_id == task.task_id and result.task_spec_sha256 == spec_sha and result.receipt_path and result.receipt_sha256_path and result.source_head_before == source_anchor and result.source_head_after == source_anchor): return record("failed", "multi_cycle.child.acceptance_invalid")
            terminal_receipt = _load_verified_child_receipt(receipt_path=Path(result.receipt_path), expected_run_id=child_id, repository_id=repository_id, task_id=task.task_id, task_spec_sha256=spec_sha, source_root=source_root, source_branch=source_branch, source_anchor=source_anchor, expected_parent=accepted_head, expected_status=result.status)
            if not terminal_receipt or terminal_receipt.get("commit_sha") != result.commit_sha or terminal_receipt.get("commit_parent_sha") != result.commit_parent_sha or terminal_receipt.get("worktree_preserved") != result.worktree_preserved: return record("failed", "multi_cycle.child.acceptance_invalid")
            return terminalize(result.status, f"multi_cycle.child.{result.status}", task, index, child_id, spec_sha, terminal_receipt)
        if result.status != "completed": return record("failed", "multi_cycle.child.failed")
        if not _receipt_valid(result, repository_id=repository_id, task_id=task.task_id, task_spec_sha256=spec_sha, source_anchor=source_anchor, accepted_head=accepted_head, source_root=source_root, source_branch=source_branch): return record("failed", "multi_cycle.child.acceptance_invalid")
        completed.append({"task_id":task.task_id,"status":"completed","reason_code":result.reason_code,"commit_sha":result.commit_sha,"parent_sha":result.commit_parent_sha,"worktree_preserved":False,"child_receipt_path":result.receipt_path})
        accepted_head = result.commit_sha; stopped_task_id = None; checkpoint("accepted_task")
        active = None
    terminal_finished_at = _utc_now()
    checkpoint("finalizing", terminal_status="completed", terminal_reason_code="multi_cycle.completed", terminal_finished_at=terminal_finished_at)
    state = {"cycle_run_id":run_id,"repository_id":repository_id,"queue_spec_sha256":queue_sha,"source_anchor_sha":source_anchor,"continuation_base_sha":continuation_base,"accepted_head_sha":accepted_head,"task_count":task_count,"completed_task_results":completed,"started_at":started,"terminal_finished_at":terminal_finished_at,"terminal_status":"completed","terminal_reason_code":"multi_cycle.completed","stopped_task_id":None}
    try:
        receipt_path, sidecar_path = _recover_terminal_pair(directory, state)
    except (OSError, ValueError):
        return RepositoryMultiCycleRunResult("1", run_id, "failed", "multi_cycle.receipt.write_failed", repository_id, str(directory / "receipt.json"), str(directory / "receipt.sha256"), source_anchor, accepted_head, len(completed), None, started, terminal_finished_at)
    return RepositoryMultiCycleRunResult("1", run_id, "completed", "multi_cycle.completed", repository_id, str(receipt_path), str(sidecar_path), source_anchor, accepted_head, len(completed), None, started, terminal_finished_at)


__all__ = ["DEFAULT_REPOSITORY_MULTI_CYCLE_OUTPUT_ROOT", "RepositoryMultiCycleRunResult", "run_repository_multi_cycle"]

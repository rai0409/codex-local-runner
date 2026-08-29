"""Authoritative, read-only classification of multi-cycle persisted evidence.

The classifier deliberately separates the semantic meaning of a cycle from
the action-specific checks performed by the executor.  In particular, a
``TASK_TERMINAL_RESUMABLE`` result establishes a verified terminal shape; the
executor still verifies the queue task-specs, child receipts, and Git parent
chain before it actually seeds a resume.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from automation.orchestration.repository_multi_cycle_status import (
    RepositoryMultiCycleStatusError,
    _read_latest_checkpoint_read_only,
    read_verified_terminal_receipt,
)


class CycleEvidenceKind(str, Enum):
    ACTIVE = "ACTIVE"
    PRE_TASK_NO_PROGRESS = "PRE_TASK_NO_PROGRESS"
    TASK_TERMINAL = "TASK_TERMINAL"
    TASK_TERMINAL_RESUMABLE = "TASK_TERMINAL_RESUMABLE"
    COMPLETED = "COMPLETED"
    INVALID = "INVALID"


@dataclass(frozen=True)
class CycleEvidence:
    evidence_kind: CycleEvidenceKind
    cycle_run_id: str | None
    repository_id: str | None
    queue_spec_sha256: str | None
    source_anchor_sha: str | None
    accepted_head_sha: str | None
    completed_count: int | None
    continuation_eligible: bool
    fresh_launch_suppressing: bool
    terminal_resume_eligible: bool
    authoritative_terminal: bool
    stopped_task_id: str | None
    reason_code: str | None
    evidence_refs: tuple[str, ...]


_SHA = re.compile(r"^[0-9a-f]{40}$")
_TERMINAL = {"blocked", "failed"}
_ACTIVE = {"initialized", "active_task", "accepted_task", "finalizing"}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _result(
    kind: CycleEvidenceKind,
    directory: Path,
    receipt: Mapping[str, Any] | None = None,
    *,
    reason: str | None = None,
    continuation: bool = False,
    suppresses_fresh: bool = False,
    resumes: bool = False,
    terminal: bool = False,
) -> CycleEvidence:
    value = receipt or {}
    return CycleEvidence(
        evidence_kind=kind,
        cycle_run_id=value.get("cycle_run_id") if isinstance(value.get("cycle_run_id"), str) else directory.name,
        repository_id=value.get("repository_id") if isinstance(value.get("repository_id"), str) else None,
        queue_spec_sha256=value.get("queue_spec_sha256") if isinstance(value.get("queue_spec_sha256"), str) else None,
        source_anchor_sha=value.get("source_anchor_sha") if _sha(value.get("source_anchor_sha")) else None,
        accepted_head_sha=value.get("final_accepted_head_sha") if _sha(value.get("final_accepted_head_sha")) else value.get("accepted_head_sha") if _sha(value.get("accepted_head_sha")) else None,
        completed_count=value.get("completed_count") if isinstance(value.get("completed_count"), int) and not isinstance(value.get("completed_count"), bool) else None,
        continuation_eligible=continuation,
        fresh_launch_suppressing=suppresses_fresh,
        terminal_resume_eligible=resumes,
        authoritative_terminal=terminal,
        stopped_task_id=value.get("stopped_task_id") if isinstance(value.get("stopped_task_id"), str) else None,
        reason_code=reason or (value.get("reason_code") if isinstance(value.get("reason_code"), str) else None),
        evidence_refs=tuple(str(path) for path in (directory / "receipt.json", directory / "receipt.sha256", directory / "state")),
    )


def _legacy_pre_task_receipt(directory: Path, repository_id: str, queue_sha256: str | None, source_anchor: str | None) -> Mapping[str, Any] | None:
    """Recognize only the historic null-final-head producer defect."""
    try:
        payload = (directory / "receipt.json").read_bytes()
        receipt = json.loads(payload)
        sidecar = (directory / "receipt.sha256").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(receipt, dict) or sidecar != f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n":
        return None
    anchor = receipt.get("source_anchor_sha")
    if not (
        receipt.get("schema_version") == "1"
        and receipt.get("cycle_run_id") == directory.name
        and receipt.get("repository_id") == repository_id
        and (queue_sha256 is None or receipt.get("queue_spec_sha256") == queue_sha256)
        and _sha(anchor)
        and (source_anchor is None or anchor == source_anchor)
        and receipt.get("continuation_base_sha") == anchor
        and receipt.get("final_accepted_head_sha") is None
        and receipt.get("reason_code") == "multi_cycle.continuation.evidence_invalid"
        and receipt.get("completed_count") == 0
        and receipt.get("executed_task_results") == []
        and receipt.get("stopped_task_id") is None
    ):
        return None
    return receipt


def _is_current_pre_task(receipt: Mapping[str, Any], source_anchor: str | None) -> bool:
    anchor = receipt.get("source_anchor_sha")
    return bool(
        receipt.get("status") in _TERMINAL
        and _sha(anchor)
        and (source_anchor is None or anchor == source_anchor)
        and receipt.get("continuation_base_sha") == anchor
        and receipt.get("final_accepted_head_sha") == anchor
        and receipt.get("pre_task_terminal") is True
        and receipt.get("completed_count") == 0
        and receipt.get("executed_task_results") == []
        and receipt.get("stopped_task_id") is None
    )


def _terminal_checkpoint_is_resumable(directory: Path, receipt: Mapping[str, Any], source_root: str | None) -> bool:
    """Verify durable terminal/child identity without interpreting queue specs.

    Queue ordering, task-spec SHA, and Git ancestry are intentionally verified
    by the terminal-resume action before it uses this classification.
    """
    try:
        state = _read_latest_checkpoint_read_only(directory)
    except RepositoryMultiCycleStatusError:
        return False
    if not isinstance(state, dict):
        return False
    terminal = state.get("terminal_task_result")
    if not isinstance(terminal, dict):
        return False
    count, completed = receipt.get("completed_count"), receipt.get("executed_task_results")
    if not (
        isinstance(count, int) and not isinstance(count, bool)
        and isinstance(completed, list) and len(completed) == count
        and state.get("cycle_run_id") == receipt.get("cycle_run_id") == directory.name
        and state.get("repository_id") == receipt.get("repository_id")
        and state.get("queue_spec_sha256") == receipt.get("queue_spec_sha256")
        and (source_root is None or state.get("source_repository_root") == source_root)
        and state.get("source_anchor_sha") == receipt.get("source_anchor_sha")
        and state.get("continuation_base_sha") == receipt.get("continuation_base_sha")
        and state.get("accepted_head_sha") == receipt.get("final_accepted_head_sha")
        and state.get("next_task_index") == count
        and state.get("completed_task_results") == completed
        and state.get("lifecycle_status") == "finalizing"
        and state.get("terminal_status") == receipt.get("status")
        and state.get("terminal_reason_code") == receipt.get("reason_code")
        and state.get("stopped_task_id") == receipt.get("stopped_task_id")
        and terminal.get("task_index") == count
        and terminal.get("task_id") == receipt.get("stopped_task_id")
        and terminal.get("status") == receipt.get("status")
        and terminal.get("commit_created") is False
        and terminal.get("commit_sha") is None
        and terminal.get("commit_parent_sha") is None
    ):
        return False
    try:
        child_path = Path(str(terminal.get("child_receipt_path", "")))
        payload = child_path.read_bytes()
        child = json.loads(payload)
        sidecar = child_path.with_name("receipt.sha256").read_text(encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    digest = hashlib.sha256(payload).hexdigest()
    return bool(
        child_path.name == "receipt.json"
        and terminal.get("child_receipt_sha256") == digest
        and sidecar == f"{digest}  receipt.json\n"
        and isinstance(child, dict)
        and child.get("repository_id") == receipt.get("repository_id")
        and child.get("task_id") == terminal.get("task_id")
        and child.get("status") == terminal.get("status")
        and child.get("commit_created") is False
        and child.get("commit_sha") is None
        and child.get("commit_parent_sha") is None
    )


def classify_cycle_evidence(directory: str | Path, repository_id: str, queue_sha256: str | None, *, source_root: str | None = None, source_anchor: str | None = None) -> CycleEvidence | None:
    """Classify one relevant cycle directory without mutating evidence.

    ``None`` means no evidence for this repository/queue identity.  ``INVALID``
    is reserved for relevant evidence that cannot safely be used.
    """
    root = Path(directory)
    try:
        receipt = read_verified_terminal_receipt(root, repository_id, queue_sha256)
    except RepositoryMultiCycleStatusError:
        legacy = _legacy_pre_task_receipt(root, repository_id, queue_sha256, source_anchor)
        if legacy is not None:
            return _result(CycleEvidenceKind.PRE_TASK_NO_PROGRESS, root, legacy)
        return _result(CycleEvidenceKind.INVALID, root, reason="multi_cycle.evidence.receipt_invalid")
    if receipt is not None:
        if source_anchor is not None and receipt.get("source_anchor_sha") != source_anchor:
            return _result(CycleEvidenceKind.INVALID, root, receipt, reason="multi_cycle.evidence.source_anchor_mismatch")
        if _is_current_pre_task(receipt, source_anchor):
            return _result(CycleEvidenceKind.PRE_TASK_NO_PROGRESS, root, receipt)
        status, count, results = receipt.get("status"), receipt.get("completed_count"), receipt.get("executed_task_results")
        if status == "completed":
            if not (count == receipt.get("task_count") and isinstance(results, list) and len(results) == count and receipt.get("stopped_task_id") is None and _sha(receipt.get("source_anchor_sha")) and _sha(receipt.get("final_accepted_head_sha"))):
                return _result(CycleEvidenceKind.INVALID, root, receipt, reason="multi_cycle.evidence.completed_invalid")
            return _result(CycleEvidenceKind.COMPLETED, root, receipt, continuation=True, suppresses_fresh=True, terminal=True)
        if status in _TERMINAL:
            if not (isinstance(count, int) and not isinstance(count, bool) and isinstance(results, list) and len(results) == count and _sha(receipt.get("source_anchor_sha")) and _sha(receipt.get("final_accepted_head_sha"))):
                return _result(CycleEvidenceKind.INVALID, root, receipt, reason="multi_cycle.evidence.terminal_invalid")
            resumable = _terminal_checkpoint_is_resumable(root, receipt, source_root)
            return _result(CycleEvidenceKind.TASK_TERMINAL_RESUMABLE if resumable else CycleEvidenceKind.TASK_TERMINAL, root, receipt, continuation=True, suppresses_fresh=True, resumes=resumable, terminal=True)
        return _result(CycleEvidenceKind.INVALID, root, receipt, reason="multi_cycle.evidence.terminal_status_invalid")
    legacy = _legacy_pre_task_receipt(root, repository_id, queue_sha256, source_anchor)
    if legacy is not None:
        return _result(CycleEvidenceKind.PRE_TASK_NO_PROGRESS, root, legacy)
    try:
        checkpoint = _read_latest_checkpoint_read_only(root)
    except RepositoryMultiCycleStatusError:
        return _result(CycleEvidenceKind.INVALID, root, reason="multi_cycle.evidence.checkpoint_invalid")
    if checkpoint is None:
        return None
    if checkpoint.get("repository_id") != repository_id or (queue_sha256 is not None and checkpoint.get("queue_spec_sha256") != queue_sha256):
        return None
    if source_anchor is not None and checkpoint.get("source_anchor_sha") != source_anchor:
        return _result(CycleEvidenceKind.INVALID, root, checkpoint, reason="multi_cycle.evidence.source_anchor_mismatch")
    if checkpoint.get("cycle_run_id") != root.name or checkpoint.get("lifecycle_status") not in _ACTIVE:
        return _result(CycleEvidenceKind.INVALID, root, checkpoint, reason="multi_cycle.evidence.active_invalid")
    return _result(CycleEvidenceKind.ACTIVE, root, checkpoint, suppresses_fresh=True)


__all__ = ["CycleEvidence", "CycleEvidenceKind", "classify_cycle_evidence"]

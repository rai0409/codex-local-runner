"""Deterministic persisted-evidence fixtures for multi-cycle classification."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from automation.orchestration.repository_multi_cycle_evidence import CycleEvidenceKind, classify_cycle_evidence
from automation.orchestration.repository_multi_cycle_state import write_checkpoint
from automation.orchestration.repository_multi_cycle_status import inspect_repository_multi_cycle_status
from automation.orchestration.repository_multi_cycle_supervisor import RepositoryMultiCycleSupervisor


ANCHOR = "a" * 40


def _receipt(directory: Path, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "1", "cycle_run_id": directory.name,
        "repository_id": "repo", "queue_spec_sha256": "q" * 64,
        "status": "blocked", "reason_code": "multi_cycle.continuation.evidence_invalid",
        "task_count": 2, "completed_count": 0, "stopped_task_id": None,
        "executed_task_results": [], "source_anchor_sha": ANCHOR,
        "continuation_base_sha": ANCHOR, "final_accepted_head_sha": ANCHOR,
    }
    value.update(overrides)
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    (directory / "receipt.json").write_bytes(payload)
    (directory / "receipt.sha256").write_text(f"{hashlib.sha256(payload).hexdigest()}  receipt.json\n")
    return value


def _queue(path: Path) -> None:
    path.write_text('{"schema_version":"1","tasks":[]}', encoding="utf-8")


def test_pre_task_no_progress_is_historical_across_classifier_supervisor_and_status(tmp_path: Path) -> None:
    queue = tmp_path / "queue.json"; _queue(queue); queue_sha = hashlib.sha256(queue.read_bytes()).hexdigest()
    cycles = tmp_path / "cycles"; current = cycles / "cycle-20260826170451541320"; current.mkdir(parents=True)
    _receipt(current, queue_spec_sha256=queue_sha, pre_task_terminal=True)
    legacy = cycles / "cycle-20260826173504196099"; legacy.mkdir()
    _receipt(legacy, queue_spec_sha256=queue_sha, final_accepted_head_sha=None)
    current_evidence = classify_cycle_evidence(current, "repo", queue_sha, source_anchor=ANCHOR)
    legacy_evidence = classify_cycle_evidence(legacy, "repo", queue_sha, source_anchor=ANCHOR)
    assert current_evidence is not None and legacy_evidence is not None
    for evidence in (current_evidence, legacy_evidence):
        assert evidence.evidence_kind is CycleEvidenceKind.PRE_TASK_NO_PROGRESS
        assert not evidence.continuation_eligible
        assert not evidence.fresh_launch_suppressing
        assert not evidence.terminal_resume_eligible
        assert not evidence.authoritative_terminal
    supervisor = RepositoryMultiCycleSupervisor("repo", queue, state_root=tmp_path / "supervisor", cycle_output_root=cycles, worker_factory=lambda _: object())
    assert supervisor._candidates(queue_sha) == ([], [], [current.name, legacy.name])
    observed = inspect_repository_multi_cycle_status("repo", queue, state_root=tmp_path / "status", cycle_output_root=cycles)
    assert observed["evidence_kind"] == "PRE_TASK_NO_PROGRESS"
    assert observed["fresh_launch_suppressing"] is False
    assert observed["terminal_resume_eligible"] is False

    other_queue = cycles / "cycle-20260826173504196100"; other_queue.mkdir()
    _receipt(other_queue, queue_spec_sha256="z" * 64, pre_task_terminal=True)
    assert classify_cycle_evidence(other_queue, "repo", queue_sha, source_anchor=ANCHOR) is None
    assert supervisor._candidates(queue_sha) == ([], [], [current.name, legacy.name])


def test_active_completed_and_corrupt_evidence_are_distinct(tmp_path: Path) -> None:
    cycles = tmp_path / "cycles"; cycles.mkdir()
    active = cycles / "cycle-20260826170451541320"; active.mkdir()
    write_checkpoint(active / "state", {"cycle_run_id": active.name, "repository_id": "repo", "queue_spec_sha256": "q" * 64, "lifecycle_status": "active_task", "source_anchor_sha": ANCHOR, "accepted_head_sha": ANCHOR})
    evidence = classify_cycle_evidence(active, "repo", "q" * 64, source_anchor=ANCHOR)
    assert evidence is not None and evidence.evidence_kind is CycleEvidenceKind.ACTIVE
    assert evidence.fresh_launch_suppressing and not evidence.terminal_resume_eligible
    completed = cycles / "cycle-20260826170451541321"; completed.mkdir()
    _receipt(completed, status="completed", task_count=0, completed_count=0, reason_code="multi_cycle.completed")
    evidence = classify_cycle_evidence(completed, "repo", "q" * 64, source_anchor=ANCHOR)
    assert evidence is not None and evidence.evidence_kind is CycleEvidenceKind.COMPLETED
    assert evidence.fresh_launch_suppressing and evidence.continuation_eligible and evidence.authoritative_terminal
    corrupt = cycles / "cycle-20260826170451541322"; corrupt.mkdir()
    _receipt(corrupt); (corrupt / "receipt.sha256").write_text("0" * 64 + "  receipt.json\n")
    evidence = classify_cycle_evidence(corrupt, "repo", "q" * 64, source_anchor=ANCHOR)
    assert evidence is not None and evidence.evidence_kind is CycleEvidenceKind.INVALID


def test_task_terminal_with_verified_child_is_resume_candidate_but_pre_task_never_is(tmp_path: Path) -> None:
    queue = tmp_path / "queue.json"; _queue(queue); queue_sha = hashlib.sha256(queue.read_bytes()).hexdigest()
    cycles = tmp_path / "cycles"; terminal = cycles / "cycle-20260827151404653031"; terminal.mkdir(parents=True)
    child = tmp_path / "children" / "run-child" / "receipt.json"; child.parent.mkdir(parents=True)
    child_value = {"repository_id": "repo", "task_id": "one", "status": "blocked", "commit_created": False, "commit_sha": None, "commit_parent_sha": None}
    child_payload = json.dumps(child_value, sort_keys=True, separators=(",", ":")).encode(); child.write_bytes(child_payload)
    child.with_name("receipt.sha256").write_text(f"{hashlib.sha256(child_payload).hexdigest()}  receipt.json\n")
    _receipt(terminal, queue_spec_sha256=queue_sha, reason_code="multi_cycle.child.blocked", stopped_task_id="one")
    write_checkpoint(terminal / "state", {"cycle_run_id": terminal.name, "repository_id": "repo", "queue_spec_sha256": queue_sha, "source_repository_root": "source", "source_anchor_sha": ANCHOR, "continuation_base_sha": ANCHOR, "accepted_head_sha": ANCHOR, "task_count": 2, "next_task_index": 0, "completed_task_results": [], "lifecycle_status": "finalizing", "terminal_status": "blocked", "terminal_reason_code": "multi_cycle.child.blocked", "stopped_task_id": "one", "terminal_task_result": {"task_index": 0, "task_id": "one", "status": "blocked", "commit_created": False, "commit_sha": None, "commit_parent_sha": None, "child_receipt_path": str(child), "child_receipt_sha256": hashlib.sha256(child_payload).hexdigest()}})
    evidence = classify_cycle_evidence(terminal, "repo", queue_sha, source_root="source", source_anchor=ANCHOR)
    assert evidence is not None and evidence.evidence_kind is CycleEvidenceKind.TASK_TERMINAL_RESUMABLE
    assert evidence.continuation_eligible and evidence.fresh_launch_suppressing and evidence.terminal_resume_eligible
    supervisor = RepositoryMultiCycleSupervisor("repo", queue, state_root=tmp_path / "supervisor", cycle_output_root=cycles, worker_factory=lambda _: object())
    assert supervisor._candidates(queue_sha) == ([], [terminal.name], [])
    observed = inspect_repository_multi_cycle_status("repo", queue, state_root=tmp_path / "status", cycle_output_root=cycles)
    assert observed["evidence_kind"] == "TASK_TERMINAL_RESUMABLE"
    assert observed["fresh_launch_suppressing"] is True
    assert observed["terminal_resume_eligible"] is True


def test_completed_and_invalid_evidence_are_consistent_for_supervisor_and_status(tmp_path: Path) -> None:
    queue = tmp_path / "queue.json"; _queue(queue); queue_sha = hashlib.sha256(queue.read_bytes()).hexdigest()
    cycles = tmp_path / "cycles"; completed = cycles / "cycle-completed"; completed.mkdir(parents=True)
    _receipt(completed, queue_spec_sha256=queue_sha, status="completed", task_count=0, completed_count=0, reason_code="multi_cycle.completed")

    completed_evidence = classify_cycle_evidence(completed, "repo", queue_sha, source_anchor=ANCHOR)
    assert completed_evidence is not None and completed_evidence.evidence_kind is CycleEvidenceKind.COMPLETED
    assert completed_evidence.fresh_launch_suppressing
    assert not completed_evidence.terminal_resume_eligible
    completed_supervisor = RepositoryMultiCycleSupervisor("repo", queue, state_root=tmp_path / "completed-supervisor", cycle_output_root=cycles, worker_factory=lambda _: object())
    assert completed_supervisor._candidates(queue_sha) == ([], [completed.name], [])
    completed_status = inspect_repository_multi_cycle_status("repo", queue, state_root=tmp_path / "completed-status", cycle_output_root=cycles)
    assert completed_status["evidence_kind"] == "COMPLETED"
    assert completed_status["fresh_launch_suppressing"] is True
    assert completed_status["terminal_resume_eligible"] is False

    invalid = cycles / "cycle-invalid"; invalid.mkdir()
    _receipt(invalid, queue_spec_sha256=queue_sha)
    (invalid / "receipt.sha256").write_text("0" * 64 + "  receipt.json\n")
    invalid_evidence = classify_cycle_evidence(invalid, "repo", queue_sha, source_anchor=ANCHOR)
    assert invalid_evidence is not None and invalid_evidence.evidence_kind is CycleEvidenceKind.INVALID
    assert not invalid_evidence.continuation_eligible
    assert not invalid_evidence.fresh_launch_suppressing
    assert not invalid_evidence.terminal_resume_eligible
    with pytest.raises(ValueError, match="supervisor.cycle.evidence_invalid"):
        completed_supervisor._candidates(queue_sha)
    invalid_status = inspect_repository_multi_cycle_status("repo", queue, state_root=tmp_path / "invalid-status", cycle_output_root=cycles)
    assert invalid_status["action_required"] is True

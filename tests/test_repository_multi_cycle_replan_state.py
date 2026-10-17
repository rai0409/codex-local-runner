from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest import mock

import pytest

import automation.orchestration.repository_multi_cycle_replan_runtime as runtime_module
import automation.orchestration.repository_multi_cycle_replan_state as state_module
from automation.orchestration.repository_multi_cycle_replan_runtime import (
    ReplanPlannerResult,
)
from automation.orchestration.repository_multi_cycle_replan_state import (
    ReplanPersistenceInput,
    load_verified_accepted_replan,
    load_verified_campaign_state,
    persist_replan_result,
)
from automation.orchestration.repository_multi_cycle_task_spec import (
    load_repository_multi_cycle_task_spec,
    serialize_repository_multi_cycle_task_spec,
    validate_repository_multi_cycle_task_spec,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _rewrite_pair(path: Path, payload: bytes) -> None:
    path.write_bytes(payload)
    path.with_suffix(".sha256").write_text(
        f"{_sha(payload)}  {path.name}\n", encoding="ascii"
    )


def _runtime(attempt: int = 1, *, prompt: str = "repair") -> ReplanPlannerResult:
    replacement_id = f"failed-replan-{attempt}"
    queue = validate_repository_multi_cycle_task_spec(
        {
            "schema_version": "1",
            "tasks": [
                {
                    "task_id": replacement_id,
                    "prompt": prompt,
                    "allowed_changed_paths": ["repair.py"],
                    "commit_message": "Repair failure",
                    "execution_timeout_seconds": 1200,
                },
                {
                    "task_id": "pending",
                    "prompt": "pending",
                    "allowed_changed_paths": ["pending.py"],
                    "commit_message": "Pending",
                },
            ],
        }
    )
    serialized = serialize_repository_multi_cycle_task_spec(queue)
    return ReplanPlannerResult(
        status="successor_ready",
        reason_code="replan.successor.ready",
        replan_attempt_number=attempt,
        validated_envelope=None,
        planner_call_count=1,
        replacement_task_id=replacement_id,
        successor_queue=queue,
        serialized_successor_queue=serialized,
        successor_queue_sha256=_sha(serialized.encode("utf-8")),
    )


def _input(runtime: ReplanPlannerResult | None = None) -> ReplanPersistenceInput:
    return ReplanPersistenceInput(
        repository_id="example/repository",
        root_queue_spec_sha256="a" * 64,
        predecessor_queue_spec_sha256="b" * 64,
        predecessor_cycle_run_id="cycle-12345678901234567890",
        failed_task_id="failed",
        failed_task_index=1,
        accepted_head_sha="c" * 40,
        reason_code="single_task.task_completion.rework_exhausted",
        detail_reason_code="contract.missing",
        runtime_result=runtime or _runtime(),
    )


def test_successor_ready_persists_and_verifies_all_artifacts(tmp_path: Path) -> None:
    value = _input()

    result = persist_replan_result(value, state_root=tmp_path)

    assert result.status == "successor_ready"
    assert result.attempt_directory is not None
    names = {path.name for path in result.attempt_directory.iterdir()}
    assert names == {
        "accepted_replan.json",
        "accepted_replan.sha256",
        "successor_queue.json",
        "successor_queue.sha256",
        "campaign.json",
        "campaign.sha256",
    }
    accepted = load_verified_accepted_replan(result.attempt_directory)
    campaign = load_verified_campaign_state(result.attempt_directory)
    assert accepted["decision"] == "replace_failed_task"
    assert campaign["state"] == "successor_ready"


def test_accepted_retains_exact_queue_and_materializes_exact_bytes(tmp_path: Path) -> None:
    value = _input()
    result = persist_replan_result(value, state_root=tmp_path)
    assert result.attempt_directory is not None
    accepted = load_verified_accepted_replan(result.attempt_directory)
    queue_path = result.attempt_directory / "successor_queue.json"
    expected = value.runtime_result.serialized_successor_queue

    assert accepted["successor_queue_serialized_content"] == expected
    assert accepted["successor_queue_sha256"] == value.runtime_result.successor_queue_sha256
    assert queue_path.read_bytes() == expected.encode("utf-8")
    assert _sha(queue_path.read_bytes()) == accepted["successor_queue_sha256"]
    assert queue_path.with_suffix(".sha256").read_text() == (
        f"{accepted['successor_queue_sha256']}  successor_queue.json\n"
    )
    assert load_repository_multi_cycle_task_spec(queue_path) == value.runtime_result.successor_queue


def test_accepted_and_campaign_checksums_cover_exact_bytes(tmp_path: Path) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.attempt_directory is not None
    for name in ("accepted_replan.json", "campaign.json"):
        path = result.attempt_directory / name
        assert path.with_suffix(".sha256").read_text() == (
            f"{_sha(path.read_bytes())}  {name}\n"
        )


def test_stop_persists_accepted_and_stopped_campaign_without_queue(tmp_path: Path) -> None:
    stopped = ReplanPlannerResult("stop", "replan.planner.stop", 1, None, 1)

    result = persist_replan_result(_input(stopped), state_root=tmp_path)

    assert result.status == "stopped"
    assert result.attempt_directory is not None
    accepted = load_verified_accepted_replan(result.attempt_directory)
    campaign = load_verified_campaign_state(result.attempt_directory)
    assert accepted["decision"] == "stop"
    assert accepted["successor_queue_serialized_content"] is None
    assert campaign["state"] == "stopped"
    assert campaign["successor_queue_path"] is None
    assert not (result.attempt_directory / "successor_queue.json").exists()


def test_blocked_creates_no_authority(tmp_path: Path) -> None:
    blocked = ReplanPlannerResult("blocked", "replan.planner.execution_failed", 1, None, 1)

    result = persist_replan_result(_input(blocked), state_root=tmp_path)

    assert result.status == "blocked"
    assert result.accepted_replan_path is None
    assert not tmp_path.exists() or not any(tmp_path.rglob("accepted_replan.json"))


def test_same_attempt_is_idempotent_without_rewriting_authority(tmp_path: Path) -> None:
    value = _input()
    first = persist_replan_result(value, state_root=tmp_path)
    assert first.accepted_replan_path is not None
    before = first.accepted_replan_path.stat()
    payload = first.accepted_replan_path.read_bytes()

    second = persist_replan_result(value, state_root=tmp_path)

    after = first.accepted_replan_path.stat()
    assert second.status == "successor_ready"
    assert second.successor_queue_sha256 == first.successor_queue_sha256
    assert second.replacement_task_id == first.replacement_task_id
    assert first.accepted_replan_path.read_bytes() == payload
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)


def test_conflicting_caller_fails_closed_and_preserves_accepted(tmp_path: Path) -> None:
    first = persist_replan_result(_input(), state_root=tmp_path)
    assert first.accepted_replan_path is not None
    before = first.accepted_replan_path.read_bytes()

    conflict = persist_replan_result(_input(_runtime(prompt="different")), state_root=tmp_path)

    assert conflict.status == "blocked"
    assert conflict.reason_code == "replan.persistence.accepted.caller_conflict"
    assert first.accepted_replan_path.read_bytes() == before


def test_attempts_are_isolated(tmp_path: Path) -> None:
    first = persist_replan_result(_input(_runtime(1)), state_root=tmp_path)
    second = persist_replan_result(_input(_runtime(2)), state_root=tmp_path)

    assert first.attempt_directory is not None and second.attempt_directory is not None
    assert first.attempt_directory.name == "attempt-001"
    assert second.attempt_directory.name == "attempt-002"
    assert first.attempt_directory != second.attempt_directory
    assert load_verified_accepted_replan(first.attempt_directory)["replacement_task_id"] == "failed-replan-1"


def test_crash_after_accepted_recovers_without_rewriting_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = state_module._write_new_pair

    def crash(path: Path, payload: bytes) -> None:
        if path.name == "successor_queue.json":
            raise RuntimeError("simulated crash")
        original(path, payload)

    monkeypatch.setattr(state_module, "_write_new_pair", crash)
    with pytest.raises(RuntimeError, match="simulated crash"):
        persist_replan_result(_input(), state_root=tmp_path)
    accepted_path = next(tmp_path.rglob("accepted_replan.json"))
    before = accepted_path.stat()
    payload = accepted_path.read_bytes()
    monkeypatch.setattr(state_module, "_write_new_pair", original)

    recovered = persist_replan_result(_input(), state_root=tmp_path)

    after = accepted_path.stat()
    assert recovered.status == "successor_ready"
    assert accepted_path.read_bytes() == payload
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert recovered.successor_queue_path is not None
    assert recovered.campaign_path is not None


def test_missing_successor_is_recovered_from_accepted_exactly(tmp_path: Path) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.successor_queue_path is not None
    accepted = load_verified_accepted_replan(result.attempt_directory)
    result.successor_queue_path.unlink()
    result.successor_queue_path.with_suffix(".sha256").unlink()

    recovered = persist_replan_result(_input(), state_root=tmp_path)

    assert recovered.successor_queue_path is not None
    assert recovered.successor_queue_path.read_bytes() == accepted[
        "successor_queue_serialized_content"
    ].encode("utf-8")


def test_missing_campaign_is_recovered(tmp_path: Path) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.campaign_path is not None
    result.campaign_path.unlink()
    result.campaign_path.with_suffix(".sha256").unlink()

    recovered = persist_replan_result(_input(), state_root=tmp_path)

    assert recovered.status == "successor_ready"
    assert recovered.campaign_path is not None
    assert load_verified_campaign_state(recovered.attempt_directory)["state"] == "successor_ready"


@pytest.mark.parametrize("kind", ["content", "sidecar"])
def test_conflicting_successor_fails_closed(
    tmp_path: Path, kind: str
) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.successor_queue_path is not None
    if kind == "content":
        result.successor_queue_path.write_bytes(b"{}")
    else:
        result.successor_queue_path.with_suffix(".sha256").write_text(
            "0" * 64 + "  successor_queue.json\n"
        )
    before = result.successor_queue_path.read_bytes()

    conflict = persist_replan_result(_input(), state_root=tmp_path)

    assert conflict.status == "blocked"
    assert result.successor_queue_path.read_bytes() == before


@pytest.mark.parametrize("kind", ["corrupt", "missing_sidecar", "malformed_sidecar"])
def test_corrupt_or_incomplete_accepted_fails_closed(tmp_path: Path, kind: str) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.accepted_replan_path is not None
    sidecar = result.accepted_replan_path.with_suffix(".sha256")
    if kind == "corrupt":
        result.accepted_replan_path.write_bytes(b"{}")
    elif kind == "missing_sidecar":
        sidecar.unlink()
    else:
        sidecar.write_text("invalid\n")
    before = result.accepted_replan_path.read_bytes()

    blocked = persist_replan_result(_input(), state_root=tmp_path)

    assert blocked.status == "blocked"
    assert result.accepted_replan_path.read_bytes() == before


def test_invalid_accepted_schema_with_valid_checksum_fails_closed(tmp_path: Path) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.accepted_replan_path is not None
    value = json.loads(result.accepted_replan_path.read_bytes())
    value["schema_version"] = "2"
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    _rewrite_pair(result.accepted_replan_path, payload)

    blocked = persist_replan_result(_input(), state_root=tmp_path)

    assert blocked.status == "blocked"
    assert blocked.reason_code == "replan.persistence.accepted.invariant"


def test_campaign_semantic_conflict_with_valid_checksum_fails_closed(tmp_path: Path) -> None:
    result = persist_replan_result(_input(), state_root=tmp_path)
    assert result.campaign_path is not None
    value = json.loads(result.campaign_path.read_bytes())
    value["state"] = "stopped"
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    _rewrite_pair(result.campaign_path, payload)

    blocked = persist_replan_result(_input(), state_root=tmp_path)

    assert blocked.status == "blocked"
    assert blocked.reason_code == "replan.persistence.campaign.authority_conflict"


def test_original_queue_files_are_immutable(tmp_path: Path) -> None:
    root_queue = tmp_path / "root-queue.json"
    predecessor_queue = tmp_path / "predecessor-queue.json"
    root_queue.write_bytes(b"root original")
    predecessor_queue.write_bytes(b"predecessor original")
    before = (root_queue.read_bytes(), predecessor_queue.read_bytes())

    result = persist_replan_result(_input(), state_root=tmp_path / "state")

    assert result.status == "successor_ready"
    assert (root_queue.read_bytes(), predecessor_queue.read_bytes()) == before


def test_persistence_has_no_planner_snapshot_git_or_worker_calls(tmp_path: Path) -> None:
    with (
        mock.patch.object(runtime_module, "run_replan_planner") as planner,
        mock.patch.object(runtime_module, "run_codex") as codex,
        mock.patch.object(runtime_module, "accepted_head_snapshot") as snapshot,
        mock.patch("subprocess.run") as subprocess_run,
    ):
        result = persist_replan_result(_input(), state_root=tmp_path)

    assert result.status == "successor_ready"
    planner.assert_not_called()
    codex.assert_not_called()
    snapshot.assert_not_called()
    subprocess_run.assert_not_called()

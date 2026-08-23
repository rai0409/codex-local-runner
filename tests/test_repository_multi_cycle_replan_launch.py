from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from automation.orchestration.repository_multi_cycle_replan_launch import (
    ReplanLaunchClaimInput,
    acquire_replan_launch_claim,
    load_verified_replan_launch_claim,
)
from automation.orchestration.repository_multi_cycle_replan_runtime import (
    ReplanPlannerResult,
)
from automation.orchestration.repository_multi_cycle_replan_state import (
    ReplanPersistenceInput,
    persist_replan_result,
)
from automation.orchestration.repository_multi_cycle_task_spec import (
    serialize_repository_multi_cycle_task_spec,
    validate_repository_multi_cycle_task_spec,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _runtime(attempt: int = 1) -> ReplanPlannerResult:
    queue = validate_repository_multi_cycle_task_spec(
        {
            "schema_version": "1",
            "tasks": [
                {
                    "task_id": f"failed-replan-{attempt}",
                    "prompt": "repair",
                    "allowed_changed_paths": ["repair.py"],
                    "commit_message": "Repair failure",
                }
            ],
        }
    )
    serialized = serialize_repository_multi_cycle_task_spec(queue)
    return ReplanPlannerResult(
        "successor_ready",
        "replan.successor.ready",
        attempt,
        None,
        1,
        f"failed-replan-{attempt}",
        queue,
        serialized,
        _sha(serialized.encode("utf-8")),
    )


def _persist(tmp_path: Path, attempt: int = 1):
    persistence_input = ReplanPersistenceInput(
        "example/repository",
        "a" * 64,
        "b" * 64,
        f"cycle-{attempt:020d}",
        "failed",
        0,
        chr(98 + attempt) * 40,
        "single_task.task_completion.rework_exhausted",
        "contract.missing",
        _runtime(attempt),
    )
    persisted = persist_replan_result(persistence_input, state_root=tmp_path)
    assert persisted.status == "successor_ready"
    return persistence_input, persisted


def _claim_input(tmp_path: Path, attempt: int = 1) -> ReplanLaunchClaimInput:
    persistence_input, persisted = _persist(tmp_path, attempt)
    return ReplanLaunchClaimInput(
        persisted, persistence_input.repository_id, persistence_input.accepted_head_sha
    )


def _rewrite_pair(path: Path, value: dict) -> None:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path.write_bytes(payload)
    path.with_suffix(".sha256").write_text(
        f"{_sha(payload)}  {path.name}\n", encoding="ascii"
    )


def test_valid_successor_creates_verified_deterministic_claim(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)

    first = acquire_replan_launch_claim(value)
    loaded = load_verified_replan_launch_claim(value)

    assert first.status == loaded.status == "launch_pending"
    assert first.launch_id == loaded.launch_id
    assert first.claim_path is not None
    payload = first.claim_path.read_bytes()
    assert first.claim_path.with_suffix(".sha256").read_text() == (
        f"{_sha(payload)}  launch_claim.json\n"
    )


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_queue_is_verified_before_claim(tmp_path: Path, damage: str) -> None:
    value = _claim_input(tmp_path)
    queue_path = value.persistence_result.successor_queue_path
    assert queue_path is not None
    if damage == "missing":
        queue_path.unlink()
    else:
        queue_path.write_bytes(b"{}")

    result = acquire_replan_launch_claim(value)

    assert result.status == "blocked"
    assert value.persistence_result.attempt_directory is not None
    assert not (value.persistence_result.attempt_directory / "launch_claim.json").exists()


def test_stopped_campaign_cannot_claim(tmp_path: Path) -> None:
    runtime = ReplanPlannerResult("stop", "replan.planner.stop", 1, None, 1)
    persistence_input = ReplanPersistenceInput(
        "example/repository", "a" * 64, "b" * 64, "cycle-00000000000000000001",
        "failed", 0, "c" * 40, "single_task.task_completion.rework_exhausted",
        None, runtime,
    )
    persisted = persist_replan_result(persistence_input, state_root=tmp_path)

    result = acquire_replan_launch_claim(
        ReplanLaunchClaimInput(persisted, "example/repository", "c" * 40)
    )

    assert result.status == "blocked"
    assert result.reason_code == "replan.launch.not_successor_ready"
    assert persisted.attempt_directory is not None
    assert not (persisted.attempt_directory / "launch_claim.json").exists()


def test_same_claim_and_restart_reuse_exact_authority(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)
    fixed = lambda: datetime(2026, 8, 23, tzinfo=timezone.utc)
    first = acquire_replan_launch_claim(value, now=fixed)
    assert first.claim_path is not None
    before = (first.claim_path.read_bytes(), first.claim_path.stat().st_mtime_ns)

    second = acquire_replan_launch_claim(
        ReplanLaunchClaimInput(
            value.persistence_result, value.repository_id, value.accepted_head_sha
        ),
        now=lambda: datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    assert second.launch_id == first.launch_id
    assert second.claim_path == first.claim_path
    assert (first.claim_path.read_bytes(), first.claim_path.stat().st_mtime_ns) == before
    assert json.loads(first.claim_path.read_bytes())["created_at"].startswith("2026-08-23")


def test_concurrent_callers_resolve_to_one_claim(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: acquire_replan_launch_claim(value), range(2)))

    assert [item.status for item in results] == ["launch_pending", "launch_pending"]
    assert len({item.launch_id for item in results}) == 1
    assert len({item.claim_path for item in results}) == 1
    assert results[0].claim_path is not None
    load_verified_replan_launch_claim(value)


def test_conflicting_input_fails_without_changing_claim(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)
    first = acquire_replan_launch_claim(value)
    assert first.claim_path is not None
    before = first.claim_path.read_bytes()
    conflicting = replace(value, accepted_head_sha="d" * 40)

    result = acquire_replan_launch_claim(conflicting)

    assert result.status == "blocked"
    assert first.claim_path.read_bytes() == before


@pytest.mark.parametrize("damage", ["json", "missing_sidecar", "wrong_sidecar"])
def test_corrupt_or_incomplete_claim_fails_without_repair(
    tmp_path: Path, damage: str
) -> None:
    value = _claim_input(tmp_path)
    first = acquire_replan_launch_claim(value)
    assert first.claim_path is not None
    sidecar = first.claim_path.with_suffix(".sha256")
    if damage == "json":
        first.claim_path.write_bytes(b"{}")
    elif damage == "missing_sidecar":
        sidecar.unlink()
    else:
        sidecar.write_text(f"{'0' * 64}  launch_claim.json\n", encoding="ascii")
    before = first.claim_path.read_bytes()

    result = acquire_replan_launch_claim(value)

    assert result.status == "blocked"
    assert first.claim_path.read_bytes() == before
    if damage == "missing_sidecar":
        assert not sidecar.exists()


def test_invalid_claim_schema_with_valid_checksum_fails(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)
    first = acquire_replan_launch_claim(value)
    assert first.claim_path is not None
    claim = json.loads(first.claim_path.read_bytes())
    claim["state"] = "launched"
    _rewrite_pair(first.claim_path, claim)

    result = acquire_replan_launch_claim(value)

    assert result.status == "blocked"


def test_attempts_have_isolated_claim_paths_and_identities(tmp_path: Path) -> None:
    first_value = _claim_input(tmp_path, 1)
    first = acquire_replan_launch_claim(first_value)
    assert first.claim_path is not None
    first_bytes = first.claim_path.read_bytes()
    second_value = _claim_input(tmp_path, 2)
    second = acquire_replan_launch_claim(second_value)

    assert second.status == "launch_pending"
    assert first.claim_path != second.claim_path
    assert first.launch_id != second.launch_id
    assert first.claim_path.read_bytes() == first_bytes


def test_r6b2_authority_remains_byte_for_byte_unchanged(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)
    attempt = value.persistence_result.attempt_directory
    assert attempt is not None
    authority_names = (
        "accepted_replan.json", "accepted_replan.sha256", "successor_queue.json",
        "successor_queue.sha256", "campaign.json", "campaign.sha256",
    )
    before = {name: (attempt / name).read_bytes() for name in authority_names}

    result = acquire_replan_launch_claim(value)

    assert result.status == "launch_pending"
    assert {name: (attempt / name).read_bytes() for name in authority_names} == before


def test_claim_layer_never_launches_worker_or_invokes_git(tmp_path: Path) -> None:
    value = _claim_input(tmp_path)
    with (
        mock.patch("subprocess.Popen") as popen,
        mock.patch("subprocess.run") as run,
        mock.patch(
            "automation.orchestration.repository_multi_cycle_supervisor.RepositoryMultiCycleSupervisor.run_once"
        ) as run_once,
    ):
        result = acquire_replan_launch_claim(value)

    assert result.status == "launch_pending"
    popen.assert_not_called()
    run.assert_not_called()
    run_once.assert_not_called()

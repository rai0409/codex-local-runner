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
)
from automation.orchestration.repository_multi_cycle_replan_launch_execution import (
    ReplanLaunchExecutionInput,
    WorkerLaunchResult,
    execute_replan_launch,
    load_verified_replan_launch_execution,
)
from automation.orchestration.repository_multi_cycle_replan_runtime import ReplanPlannerResult
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


def _value(tmp_path: Path) -> ReplanLaunchExecutionInput:
    queue = validate_repository_multi_cycle_task_spec(
        {"schema_version": "1", "tasks": [{
            "task_id": "failed-replan-1", "prompt": "repair",
            "allowed_changed_paths": ["repair.py"], "commit_message": "Repair",
        }]}
    )
    serialized = serialize_repository_multi_cycle_task_spec(queue)
    runtime = ReplanPlannerResult(
        "successor_ready", "replan.successor.ready", 1, None, 1,
        "failed-replan-1", queue, serialized, _sha(serialized.encode()),
    )
    persistence_input = ReplanPersistenceInput(
        "example/repository", "a" * 64, "b" * 64,
        "cycle-00000000000000000001", "failed", 0, "c" * 40,
        "single_task.task_completion.rework_exhausted", "contract.missing", runtime,
    )
    persisted = persist_replan_result(persistence_input, state_root=tmp_path)
    claim_input = ReplanLaunchClaimInput(persisted, "example/repository", "c" * 40)
    claim = acquire_replan_launch_claim(claim_input)
    assert claim.status == "launch_pending"
    return ReplanLaunchExecutionInput(claim_input, claim)


def _confirmed(request) -> WorkerLaunchResult:
    return WorkerLaunchResult("confirmed_started", 4321, "cycle-20260823000000000001")


def _rewrite_pair(path: Path, value: dict) -> None:
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    path.write_bytes(payload)
    path.with_suffix(".sha256").write_text(
        f"{_sha(payload)}  {path.name}\n", encoding="ascii"
    )


def test_confirmed_launch_is_durable_and_retains_worker_identity(tmp_path: Path) -> None:
    value = _value(tmp_path)
    calls = []

    result = execute_replan_launch(
        value, worker_launcher=lambda request: calls.append(request) or _confirmed(request)
    )
    loaded = load_verified_replan_launch_execution(value)

    assert result.status == loaded.status == "launched"
    assert result.launcher_call_count == 1
    assert (result.worker_pid, result.cycle_run_id) == (
        4321, "cycle-20260823000000000001"
    )
    assert result.execution_path is not None
    payload = result.execution_path.read_bytes()
    assert result.execution_path.with_suffix(".sha256").read_text() == (
        f"{_sha(payload)}  launch_execution.json\n"
    )


def test_launching_is_verified_before_launcher_and_attempt_id_is_deterministic(
    tmp_path: Path,
) -> None:
    value = _value(tmp_path)
    observed = []

    def launcher(request):
        execution = value.claim_result.claim_path.with_name("launch_execution.json")
        observed.append(json.loads(execution.read_bytes()))
        assert load_verified_replan_launch_execution(value).status == "launch_uncertain"
        return _confirmed(request)

    first = execute_replan_launch(value, worker_launcher=launcher)

    assert observed[0]["state"] == "launching"
    assert observed[0]["launch_attempt_id"] == first.launch_attempt_id
    assert first.launch_attempt_id == _sha(
        json.dumps({"launch_id": first.launch_id}, sort_keys=True, separators=(",", ":")).encode()
    )


def test_repeated_launched_reuses_identity_without_launcher(tmp_path: Path) -> None:
    value = _value(tmp_path)
    fixed = lambda: datetime(2026, 8, 23, tzinfo=timezone.utc)
    first = execute_replan_launch(value, worker_launcher=_confirmed, now=fixed)
    assert first.execution_path is not None
    before = first.execution_path.read_bytes()
    launcher = mock.Mock()

    second = execute_replan_launch(value, worker_launcher=launcher)

    assert second.status == "launched"
    assert second.launcher_call_count == 0
    assert second.launch_attempt_id == first.launch_attempt_id
    assert (second.worker_pid, second.cycle_run_id) == (first.worker_pid, first.cycle_run_id)
    assert second.execution_path.read_bytes() == before


@pytest.mark.parametrize("outcome", ["exception", "not_confirmed"])
def test_ambiguous_launcher_becomes_uncertain_and_never_retries(
    tmp_path: Path, outcome: str
) -> None:
    value = _value(tmp_path)
    calls = []

    def launcher(request):
        calls.append(request)
        if outcome == "exception":
            raise RuntimeError("unsafe detail")
        return WorkerLaunchResult("not_confirmed")

    first = execute_replan_launch(value, worker_launcher=launcher)
    second_launcher = mock.Mock()
    second = execute_replan_launch(value, worker_launcher=second_launcher)

    assert first.status == second.status == "launch_uncertain"
    assert first.reason_code == "replan.launch.execution_uncertain"
    assert len(calls) == 1
    assert second.launcher_call_count == 0
    second_launcher.assert_not_called()


def test_restart_from_launching_does_not_relaunch(tmp_path: Path) -> None:
    value = _value(tmp_path)
    with mock.patch(
        "automation.orchestration.repository_multi_cycle_replan_launch_execution._validate_launcher_result",
        side_effect=KeyboardInterrupt,
    ):
        first = execute_replan_launch(
            value, worker_launcher=lambda request: WorkerLaunchResult("confirmed_started")
        )
    assert first.status == "launch_uncertain"
    execution = value.claim_result.claim_path.with_name("launch_execution.json")
    record = json.loads(execution.read_bytes())
    record["state"] = "launching"
    record["uncertain_reason_code"] = None
    _rewrite_pair(execution, record)
    launcher = mock.Mock()

    restarted = execute_replan_launch(value, worker_launcher=launcher)

    assert restarted.status == "launch_uncertain"
    assert restarted.reason_code == "replan.launch.execution_unreconciled"
    assert restarted.launcher_call_count == 0
    launcher.assert_not_called()


def test_concurrent_same_claim_calls_launcher_once(tmp_path: Path) -> None:
    value = _value(tmp_path)
    launcher = mock.Mock(side_effect=_confirmed)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(
            lambda _: execute_replan_launch(value, worker_launcher=launcher), range(2)
        ))

    assert launcher.call_count == 1
    assert {item.status for item in results} == {"launched"}
    assert len({item.launch_attempt_id for item in results}) == 1


@pytest.mark.parametrize("damage", ["json", "missing", "wrong", "schema", "identity"])
def test_invalid_execution_authority_blocks_without_launcher(
    tmp_path: Path, damage: str
) -> None:
    value = _value(tmp_path)
    first = execute_replan_launch(value, worker_launcher=_confirmed)
    assert first.execution_path is not None
    path, sidecar = first.execution_path, first.execution_path.with_suffix(".sha256")
    if damage == "json":
        path.write_bytes(b"{}")
    elif damage == "missing":
        sidecar.unlink()
    elif damage == "wrong":
        sidecar.write_text(f"{'0' * 64}  launch_execution.json\n", encoding="ascii")
    else:
        record = json.loads(path.read_bytes())
        record["state" if damage == "schema" else "launch_id"] = (
            "running" if damage == "schema" else "0" * 64
        )
        _rewrite_pair(path, record)
    before = path.read_bytes()
    launcher = mock.Mock()

    result = execute_replan_launch(value, worker_launcher=launcher)

    assert result.status == "blocked"
    assert path.read_bytes() == before
    launcher.assert_not_called()


def test_invalid_claim_or_successor_blocks_before_launcher(tmp_path: Path) -> None:
    for damage in ("claim", "successor"):
        case = tmp_path / damage
        value = _value(case)
        if damage == "claim":
            value.claim_result.claim_path.write_bytes(b"{}")
        else:
            value.claim_result.successor_queue_path.write_bytes(b"{}")
        launcher = mock.Mock()

        result = execute_replan_launch(value, worker_launcher=launcher)

        assert result.status == "blocked"
        launcher.assert_not_called()


@pytest.mark.parametrize("outcome", ["launched", "uncertain"])
def test_claim_and_r6b2_authority_are_immutable(tmp_path: Path, outcome: str) -> None:
    value = _value(tmp_path)
    attempt = value.claim_input.persistence_result.attempt_directory
    assert attempt is not None
    names = (
        "launch_claim.json", "launch_claim.sha256", "accepted_replan.json",
        "accepted_replan.sha256", "successor_queue.json", "successor_queue.sha256",
        "campaign.json", "campaign.sha256",
    )
    before = {name: (attempt / name).read_bytes() for name in names}
    launcher = _confirmed if outcome == "launched" else lambda request: WorkerLaunchResult("not_confirmed")

    execute_replan_launch(value, worker_launcher=launcher)

    assert {name: (attempt / name).read_bytes() for name in names} == before


def test_execution_layer_calls_no_planner_git_or_supervisor(tmp_path: Path) -> None:
    value = _value(tmp_path)
    with (
        mock.patch("subprocess.Popen") as popen,
        mock.patch("subprocess.run") as run,
        mock.patch(
            "automation.orchestration.repository_multi_cycle_supervisor.RepositoryMultiCycleSupervisor.run_once"
        ) as run_once,
        mock.patch(
            "automation.orchestration.repository_multi_cycle_replan_coordinator.coordinate_verified_terminal_replan"
        ) as coordinator,
    ):
        result = execute_replan_launch(value, worker_launcher=_confirmed)

    assert result.status == "launched"
    popen.assert_not_called()
    run.assert_not_called()
    run_once.assert_not_called()
    coordinator.assert_not_called()

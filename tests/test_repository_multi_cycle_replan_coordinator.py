from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from automation.orchestration.repository_multi_cycle_replan import (
    build_successor_queue,
    validate_replan_envelope,
)
from automation.orchestration.repository_multi_cycle_replan_coordinator import (
    VerifiedTerminalReplanInput,
    coordinate_verified_terminal_replan,
)
from automation.orchestration.repository_multi_cycle_replan_runtime import (
    ReplanPlannerRequest,
    ReplanPlannerResult,
)
from automation.orchestration.repository_multi_cycle_replan_state import (
    ReplanPersistenceResult,
)


ELIGIBLE = "single_task.task_completion.rework_exhausted"


def _queue(path: Path) -> str:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "tasks": [
                    {
                        "task_id": "done",
                        "prompt": "done",
                        "allowed_changed_paths": ["done.py"],
                        "commit_message": "Done",
                    },
                    {
                        "task_id": "failed",
                        "prompt": "failed",
                        "allowed_changed_paths": ["failed.py"],
                        "commit_message": "Failed",
                        "execution_timeout_seconds": 1200,
                    },
                    {
                        "task_id": "pending",
                        "prompt": "pending",
                        "allowed_changed_paths": ["pending.py"],
                        "commit_message": "Pending",
                    },
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _terminal(
    *,
    reason: str = ELIGIBLE,
    task_id: str = "failed",
    cycle_run_id: str = "cycle-20260823000000000001",
    accepted_head: str = "c" * 40,
    queue_sha: str,
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "cycle_run_id": cycle_run_id,
        "repository_id": "repo",
        "queue_spec_sha256": queue_sha,
        "status": "blocked",
        "reason_code": "multi_cycle.child.blocked",
        "completed_count": 1,
        "stopped_task_id": task_id,
        "final_accepted_head_sha": accepted_head,
        "terminal_task_result": {
            "task_index": 1,
            "task_id": task_id,
            "status": "blocked",
            "reason_code": reason,
        },
        "detail_reason_code": "contract.missing",
        "completion_evaluation": {
            "status": "blocked",
            "reason_code": "contract.missing",
            "unsatisfied_criteria": ["missing"],
            "satisfied_criteria": [],
            "rework_attempted": True,
            "rework_validation_status": "failed",
            "rework_validation_reason": "still missing",
            "raw_log": "SECRET RAW LOG",
            "stderr": "SECRET STDERR",
            "environment": {"TOKEN": "SECRET"},
        },
    }


def _input(
    tmp_path: Path,
    *,
    terminal: dict[str, Any] | None = None,
) -> VerifiedTerminalReplanInput:
    queue_path = tmp_path / "queue.json"
    queue_sha = _queue(queue_path)
    return VerifiedTerminalReplanInput(
        repository_id="repo",
        source_repository_root=tmp_path / "source",
        root_queue_spec_path=queue_path,
        root_queue_spec_sha256="a" * 64,
        predecessor_queue_spec_path=queue_path,
        predecessor_queue_spec_sha256=queue_sha,
        verified_terminal_result=terminal or _terminal(queue_sha=queue_sha),
        replan_state_root=tmp_path / "replans",
    )


class _Planner:
    def __init__(self, outcome: str = "successor_ready") -> None:
        self.outcome = outcome
        self.calls: list[ReplanPlannerRequest] = []

    def __call__(self, request: ReplanPlannerRequest) -> ReplanPlannerResult:
        self.calls.append(request)
        if self.outcome == "blocked":
            return ReplanPlannerResult(
                "blocked", "replan.planner.execution_failed", request.replan_attempt_number,
                None, 1,
            )
        if self.outcome == "stop":
            return ReplanPlannerResult(
                "stop", "replan.planner.stop", request.replan_attempt_number, None, 1
            )
        envelope = validate_replan_envelope(
            {
                "schema_version": "1",
                "decision": "replace_failed_task",
                "prompt": "repair",
                "allowed_changed_paths": ["failed.py"],
                "commit_message": "Repair",
            }
        )
        plan = build_successor_queue(
            request.evidence, envelope, request.replan_attempt_number
        )
        assert plan.replacement_task and plan.successor_queue
        assert plan.serialized_successor_queue and plan.successor_queue_sha256
        return ReplanPlannerResult(
            "successor_ready",
            "replan.successor.ready",
            request.replan_attempt_number,
            envelope,
            1,
            plan.replacement_task.task_id,
            plan.successor_queue,
            plan.serialized_successor_queue,
            plan.successor_queue_sha256,
        )


def test_noneligible_terminal_calls_neither_planner_nor_persistence(tmp_path: Path) -> None:
    value = _input(tmp_path)
    terminal = _terminal(reason="single_task.source.dirty", queue_sha=value.predecessor_queue_spec_sha256)
    value = _input(tmp_path, terminal=terminal)
    planner, persistence = mock.Mock(), mock.Mock()

    result = coordinate_verified_terminal_replan(
        value, planner_pipeline=planner, persistence_pipeline=persistence
    )

    assert result.status == "not_eligible"
    assert result.planner_call_count == 0
    planner.assert_not_called()
    persistence.assert_not_called()


def test_eligible_success_forwards_failed_task_and_authoritative_head(tmp_path: Path) -> None:
    value = _input(tmp_path)
    planner = _Planner()

    result = coordinate_verified_terminal_replan(value, planner_pipeline=planner)

    assert result.status == "successor_ready"
    assert result.failed_task_id == "failed"
    assert result.accepted_head_sha == "c" * 40
    assert result.replan_attempt_number == 1
    assert result.planner_call_count == 1
    request = planner.calls[0]
    assert request.accepted_head_sha == value.verified_terminal_result["final_accepted_head_sha"]
    assert request.evidence.failed_task_index == 1
    assert request.evidence.predecessor_queue.tasks[1].task_id == "failed"


def test_safe_evidence_filter_excludes_logs_secrets_and_environment(tmp_path: Path) -> None:
    planner = _Planner()

    coordinate_verified_terminal_replan(_input(tmp_path), planner_pipeline=planner)

    evidence = dict(planner.calls[0].evidence.completion_evidence or {})
    assert set(evidence) == {
        "status",
        "reason_code",
        "unsatisfied_criteria",
        "satisfied_criteria",
        "rework_attempted",
        "rework_validation_status",
        "rework_validation_reason",
    }
    assert "SECRET" not in json.dumps(evidence)


def test_failed_task_mismatch_blocks_before_planner(tmp_path: Path) -> None:
    value = _input(tmp_path)
    terminal = _terminal(task_id="other", queue_sha=value.predecessor_queue_spec_sha256)
    planner = _Planner()

    result = coordinate_verified_terminal_replan(
        _input(tmp_path, terminal=terminal), planner_pipeline=planner
    )

    assert result.status == "blocked"
    assert planner.calls == []


def test_predecessor_queue_sha_mismatch_blocks_before_planner(tmp_path: Path) -> None:
    value = _input(tmp_path)
    Path(value.predecessor_queue_spec_path).write_text("{}", encoding="utf-8")
    planner = _Planner()

    result = coordinate_verified_terminal_replan(value, planner_pipeline=planner)

    assert result.status == "blocked"
    assert planner.calls == []


def test_same_event_reuses_durable_result_without_planner(tmp_path: Path) -> None:
    value = _input(tmp_path)
    first_planner = _Planner()
    first = coordinate_verified_terminal_replan(value, planner_pipeline=first_planner)
    repeat_planner = _Planner()

    repeated = coordinate_verified_terminal_replan(
        value, planner_pipeline=repeat_planner
    )

    assert first.status == repeated.status == "successor_ready"
    assert repeated.replan_attempt_number == 1
    assert repeated.planner_call_count == 0
    assert repeat_planner.calls == []
    assert repeated.successor_queue_sha256 == first.successor_queue_sha256


def test_distinct_later_event_increments_attempt_without_budget_policy(tmp_path: Path) -> None:
    first_input = _input(tmp_path)
    coordinate_verified_terminal_replan(first_input, planner_pipeline=_Planner())
    terminal = _terminal(
        queue_sha=first_input.predecessor_queue_spec_sha256,
        cycle_run_id="cycle-20260823000000000002",
    )
    second_input = _input(tmp_path, terminal=terminal)
    planner = _Planner()

    result = coordinate_verified_terminal_replan(second_input, planner_pipeline=planner)

    assert result.status == "successor_ready"
    assert result.replan_attempt_number == 2
    assert planner.calls[0].replan_attempt_number == 2


def test_first_and_second_attempt_are_allowed_with_budget_two(tmp_path: Path) -> None:
    first_input = _input(tmp_path)
    first_planner = _Planner()
    first = coordinate_verified_terminal_replan(
        first_input, max_auto_replans=2, planner_pipeline=first_planner
    )
    second_input = _input(
        tmp_path,
        terminal=_terminal(
            queue_sha=first_input.predecessor_queue_spec_sha256,
            cycle_run_id="cycle-20260823000000000002",
        ),
    )
    second_planner = _Planner()
    second = coordinate_verified_terminal_replan(
        second_input, max_auto_replans=2, planner_pipeline=second_planner
    )

    assert first.replan_attempt_number == 1
    assert second.replan_attempt_number == 2
    assert len(first_planner.calls) == len(second_planner.calls) == 1


def test_third_attempt_is_rejected_before_planner_or_persistence(tmp_path: Path) -> None:
    first_input = _input(tmp_path)
    coordinate_verified_terminal_replan(first_input, planner_pipeline=_Planner())
    second_input = _input(
        tmp_path,
        terminal=_terminal(
            queue_sha=first_input.predecessor_queue_spec_sha256,
            cycle_run_id="cycle-20260823000000000002",
        ),
    )
    coordinate_verified_terminal_replan(second_input, planner_pipeline=_Planner())
    campaign_before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (tmp_path / "replans").rglob("*")
        if path.is_file()
    }
    third_input = _input(
        tmp_path,
        terminal=_terminal(
            queue_sha=first_input.predecessor_queue_spec_sha256,
            cycle_run_id="cycle-20260823000000000003",
        ),
    )
    planner, persistence = _Planner(), mock.Mock()

    result = coordinate_verified_terminal_replan(
        third_input,
        max_auto_replans=2,
        planner_pipeline=planner,
        persistence_pipeline=persistence,
    )

    assert result.status == "blocked"
    assert result.reason_code == "replan.budget_exhausted"
    assert result.replan_attempt_number == 3
    assert result.planner_call_count == 0
    assert planner.calls == []
    persistence.assert_not_called()
    assert campaign_before == {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (tmp_path / "replans").rglob("*")
        if path.is_file()
    }


def test_same_event_at_budget_limit_is_reused(tmp_path: Path) -> None:
    first_input = _input(tmp_path)
    coordinate_verified_terminal_replan(first_input, planner_pipeline=_Planner())
    second_input = _input(
        tmp_path,
        terminal=_terminal(
            queue_sha=first_input.predecessor_queue_spec_sha256,
            cycle_run_id="cycle-20260823000000000002",
        ),
    )
    coordinate_verified_terminal_replan(second_input, planner_pipeline=_Planner())
    planner = _Planner()

    result = coordinate_verified_terminal_replan(
        second_input, max_auto_replans=2, planner_pipeline=planner
    )

    assert result.status == "successor_ready"
    assert result.replan_attempt_number == 2
    assert result.reason_code != "replan.budget_exhausted"
    assert result.planner_call_count == 0
    assert planner.calls == []


@pytest.mark.parametrize("budget", [0, -1, 9, True])
def test_invalid_internal_budget_blocks_before_planner(
    tmp_path: Path, budget: Any
) -> None:
    planner, persistence = _Planner(), mock.Mock()

    result = coordinate_verified_terminal_replan(
        _input(tmp_path),
        max_auto_replans=budget,
        planner_pipeline=planner,
        persistence_pipeline=persistence,
    )

    assert result.status == "blocked"
    assert result.reason_code == "replan.coordinator.budget_invalid"
    assert planner.calls == []
    persistence.assert_not_called()


def test_noneligible_terminal_ignores_budget(tmp_path: Path) -> None:
    value = _input(tmp_path)
    terminal = _terminal(
        reason="single_task.source.dirty",
        queue_sha=value.predecessor_queue_spec_sha256,
    )
    planner = _Planner()

    result = coordinate_verified_terminal_replan(
        _input(tmp_path, terminal=terminal),
        max_auto_replans=0,
        planner_pipeline=planner,
    )

    assert result.status == "not_eligible"
    assert planner.calls == []


def test_planner_correction_call_count_does_not_consume_campaign_attempt(
    tmp_path: Path,
) -> None:
    class TwoCallPlanner(_Planner):
        def __call__(self, request: ReplanPlannerRequest) -> ReplanPlannerResult:
            result = super().__call__(request)
            return ReplanPlannerResult(
                result.status,
                result.reason_code,
                result.replan_attempt_number,
                result.validated_envelope,
                2,
                result.replacement_task_id,
                result.successor_queue,
                result.serialized_successor_queue,
                result.successor_queue_sha256,
            )

    result = coordinate_verified_terminal_replan(
        _input(tmp_path), max_auto_replans=1, planner_pipeline=TwoCallPlanner()
    )

    assert result.status == "successor_ready"
    assert result.replan_attempt_number == 1
    assert result.planner_call_count == 2


def test_corrupt_campaign_blocks_without_planner(tmp_path: Path) -> None:
    value = _input(tmp_path)
    first = coordinate_verified_terminal_replan(value, planner_pipeline=_Planner())
    assert first.successor_queue_path is not None
    campaign = first.successor_queue_path.with_name("campaign.json")
    campaign.write_bytes(b"{}")
    planner = _Planner()

    result = coordinate_verified_terminal_replan(value, planner_pipeline=planner)

    assert result.status == "blocked"
    assert planner.calls == []


def test_planner_stop_is_durably_persisted(tmp_path: Path) -> None:
    result = coordinate_verified_terminal_replan(
        _input(tmp_path), planner_pipeline=_Planner("stop")
    )

    assert result.status == "stopped"
    assert result.successor_queue_path is None
    assert any((tmp_path / "replans").rglob("accepted_replan.json"))
    assert any((tmp_path / "replans").rglob("campaign.json"))


def test_planner_blocked_does_not_create_accepted_authority(tmp_path: Path) -> None:
    result = coordinate_verified_terminal_replan(
        _input(tmp_path), planner_pipeline=_Planner("blocked")
    )

    assert result.status == "blocked"
    assert not any((tmp_path / "replans").rglob("accepted_replan.json"))


def test_persistence_failure_blocks_without_planner_retry(tmp_path: Path) -> None:
    planner = _Planner()
    persistence = mock.Mock(
        return_value=ReplanPersistenceResult(
            "blocked", "replan.persistence.conflict", None, None, None, None,
            None, None, 1, None,
        )
    )

    result = coordinate_verified_terminal_replan(
        _input(tmp_path), planner_pipeline=planner, persistence_pipeline=persistence
    )

    assert result.status == "blocked"
    assert len(planner.calls) == 1
    assert persistence.call_count == 1


def test_coordinator_never_launches_supervisor_or_worker(tmp_path: Path) -> None:
    with (
        mock.patch(
            "automation.orchestration.repository_multi_cycle_supervisor.RepositoryMultiCycleSupervisor.run_once"
        ) as run_once,
        mock.patch(
            "automation.orchestration.repository_multi_cycle_supervisor.RepositoryMultiCycleSupervisor.run_forever"
        ) as run_forever,
        mock.patch("subprocess.Popen") as popen,
    ):
        result = coordinate_verified_terminal_replan(
            _input(tmp_path), planner_pipeline=_Planner()
        )

    assert result.status == "successor_ready"
    run_once.assert_not_called()
    run_forever.assert_not_called()
    popen.assert_not_called()

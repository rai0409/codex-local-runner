"""Coordinate verified terminal evidence through the existing R6-B pipeline."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from automation.orchestration.repository_multi_cycle_replan import (
    ReplanFailureEvidence,
    is_auto_replan_eligible,
)
from automation.orchestration.repository_multi_cycle_replan_runtime import (
    ReplanPlannerRequest,
    ReplanPlannerResult,
    run_replan_planner,
)
from automation.orchestration.repository_multi_cycle_replan_state import (
    DEFAULT_STATE_ROOT,
    ReplanPersistenceInput,
    ReplanPersistenceResult,
    _campaign_id,
    _digest,
    load_verified_accepted_replan,
    load_verified_campaign_state,
    persist_replan_result,
)
from automation.orchestration.repository_multi_cycle_task_spec import (
    load_repository_multi_cycle_task_spec,
    validate_repository_multi_cycle_task_spec,
)


_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_CYCLE_RUN_ID = re.compile(r"cycle-[0-9]{20}")
_ATTEMPT = re.compile(r"attempt-([0-9]{3})")
_SAFE_EVIDENCE_FIELDS = frozenset(
    {
        "status",
        "reason_code",
        "unsatisfied_criteria",
        "satisfied_criteria",
        "rework_attempted",
        "rework_validation_status",
        "rework_validation_reason",
        "declared_allowed_changed_paths",
        "effective_allowed_changed_paths",
        "original_unexpected_changed_files",
        "auto_expanded_paths",
        "scope_trimmed_paths",
        "scope_constrained_rework_attempted",
        "scope_constrained_rework_status",
        "post_trim_validation_status",
    }
)

PlannerPipeline = Callable[[ReplanPlannerRequest], ReplanPlannerResult]
PersistencePipeline = Callable[..., ReplanPersistenceResult]


class RepositoryMultiCycleReplanCoordinatorError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True)
class VerifiedTerminalReplanInput:
    """Evidence already verified by the receipt/checkpoint trust boundary."""

    repository_id: str
    source_repository_root: str | Path
    root_queue_spec_path: str | Path
    root_queue_spec_sha256: str
    predecessor_queue_spec_path: str | Path
    predecessor_queue_spec_sha256: str
    verified_terminal_result: Mapping[str, Any]
    replan_state_root: str | Path = DEFAULT_STATE_ROOT


@dataclass(frozen=True)
class RepositoryMultiCycleReplanCoordinatorResult:
    status: str
    reason_code: str
    replan_attempt_number: int | None
    failed_task_id: str | None
    accepted_head_sha: str | None
    successor_queue_path: Path | None
    successor_queue_sha256: str | None
    campaign_id: str | None
    planner_call_count: int


@dataclass(frozen=True)
class _TerminalEvent:
    cycle_run_id: str
    reason_code: str
    detail_reason_code: str | None
    failed_task_index: int
    failed_task_id: str
    accepted_head_sha: str
    completion_evidence: Mapping[str, Any]


def _blocked(reason_code: str) -> RepositoryMultiCycleReplanCoordinatorResult:
    return RepositoryMultiCycleReplanCoordinatorResult(
        "blocked", reason_code, None, None, None, None, None, None, 0
    )


def _extract_terminal_event(value: VerifiedTerminalReplanInput) -> _TerminalEvent:
    terminal = value.verified_terminal_result
    if not isinstance(terminal, Mapping):
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.terminal_evidence_invalid"
        )
    task = terminal.get("terminal_task_result")
    if not isinstance(task, Mapping):
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.terminal_evidence_invalid"
        )
    reason = task.get("reason_code")
    if not isinstance(reason, str) or not reason:
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.terminal_evidence_invalid"
        )
    completion = terminal.get("completion_evaluation")
    safe = (
        {key: completion[key] for key in _SAFE_EVIDENCE_FIELDS if key in completion}
        if isinstance(completion, Mapping)
        else {}
    )
    detail = terminal.get("detail_reason_code")
    if detail is None and isinstance(safe.get("reason_code"), str):
        detail = safe["reason_code"]
    if detail is not None and (not isinstance(detail, str) or not detail):
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.terminal_evidence_invalid"
        )
    event = _TerminalEvent(
        terminal.get("cycle_run_id"),
        reason,
        detail,
        task.get("task_index"),
        task.get("task_id"),
        terminal.get("final_accepted_head_sha"),
        safe,
    )
    if (
        not isinstance(event.cycle_run_id, str)
        or not _CYCLE_RUN_ID.fullmatch(event.cycle_run_id)
        or not isinstance(event.failed_task_index, int)
        or isinstance(event.failed_task_index, bool)
        or event.failed_task_index < 0
        or not isinstance(event.failed_task_id, str)
        or not event.failed_task_id
        or not isinstance(event.accepted_head_sha, str)
        or not _COMMIT_SHA.fullmatch(event.accepted_head_sha)
        or terminal.get("repository_id") != value.repository_id
        or terminal.get("queue_spec_sha256") != value.predecessor_queue_spec_sha256
        or terminal.get("completed_count") != event.failed_task_index
        or terminal.get("stopped_task_id") != event.failed_task_id
        or task.get("status") not in {"blocked", "failed"}
    ):
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.terminal_evidence_invalid"
        )
    return event


def _campaign_directory(value: VerifiedTerminalReplanInput) -> Path:
    return (
        Path(value.replan_state_root).expanduser()
        / _digest(value.repository_id.encode("utf-8"))
        / _campaign_id(value.repository_id, value.root_queue_spec_sha256)
    )


def _load_attempts(
    value: VerifiedTerminalReplanInput,
) -> list[tuple[int, Path, dict[str, Any], dict[str, Any]]]:
    campaign = _campaign_directory(value)
    if not campaign.exists():
        return []
    try:
        entries = list(campaign.iterdir())
    except OSError as exc:
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.campaign_invalid"
        ) from exc
    attempts: list[tuple[int, Path, dict[str, Any], dict[str, Any]]] = []
    for path in entries:
        match = _ATTEMPT.fullmatch(path.name)
        if match is None or not path.is_dir():
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.campaign_invalid"
            )
        number = int(match.group(1))
        try:
            accepted = load_verified_accepted_replan(path)
            state = load_verified_campaign_state(path)
        except ValueError as exc:
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.campaign_invalid"
            ) from exc
        if (
            accepted.get("repository_id") != value.repository_id
            or accepted.get("root_queue_spec_sha256") != value.root_queue_spec_sha256
            or accepted.get("replan_attempt_number") != number
            or state.get("current_attempt_number") != number
        ):
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.campaign_invalid"
            )
        attempts.append((number, path, accepted, state))
    attempts.sort(key=lambda item: item[0])
    if [item[0] for item in attempts] != list(range(1, len(attempts) + 1)):
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.campaign_invalid"
        )
    return attempts


def _same_event(accepted: Mapping[str, Any], event: _TerminalEvent, queue_sha: str) -> bool:
    return (
        accepted.get("predecessor_cycle_run_id") == event.cycle_run_id
        and accepted.get("failed_task_id") == event.failed_task_id
        and accepted.get("predecessor_queue_spec_sha256") == queue_sha
        and accepted.get("accepted_head_sha") == event.accepted_head_sha
    )


def _rehydrate_runtime(accepted: Mapping[str, Any]) -> ReplanPlannerResult:
    if accepted["decision"] == "stop":
        return ReplanPlannerResult(
            "stop",
            "replan.planner.stop",
            accepted["replan_attempt_number"],
            None,
            accepted["planner_call_count"],
        )
    serialized = accepted["successor_queue_serialized_content"]
    try:
        queue = validate_repository_multi_cycle_task_spec(json.loads(serialized))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RepositoryMultiCycleReplanCoordinatorError(
            "replan.coordinator.campaign_invalid"
        ) from exc
    return ReplanPlannerResult(
        "successor_ready",
        "replan.successor.ready",
        accepted["replan_attempt_number"],
        None,
        accepted["planner_call_count"],
        accepted["replacement_task_id"],
        queue,
        serialized,
        accepted["successor_queue_sha256"],
    )


def _persistence_input(
    value: VerifiedTerminalReplanInput,
    event: _TerminalEvent,
    runtime: ReplanPlannerResult,
) -> ReplanPersistenceInput:
    return ReplanPersistenceInput(
        value.repository_id,
        value.root_queue_spec_sha256,
        value.predecessor_queue_spec_sha256,
        event.cycle_run_id,
        event.failed_task_id,
        event.failed_task_index,
        event.accepted_head_sha,
        event.reason_code,
        event.detail_reason_code,
        runtime,
    )


def _result_from_persistence(
    persisted: ReplanPersistenceResult,
    event: _TerminalEvent,
    planner_calls: int,
) -> RepositoryMultiCycleReplanCoordinatorResult:
    if persisted.status not in {"successor_ready", "stopped"}:
        return RepositoryMultiCycleReplanCoordinatorResult(
            "blocked",
            persisted.reason_code,
            persisted.replan_attempt_number,
            event.failed_task_id,
            event.accepted_head_sha,
            None,
            None,
            None,
            planner_calls,
        )
    return RepositoryMultiCycleReplanCoordinatorResult(
        persisted.status,
        persisted.reason_code,
        persisted.replan_attempt_number,
        event.failed_task_id,
        event.accepted_head_sha,
        persisted.successor_queue_path,
        persisted.successor_queue_sha256,
        persisted.campaign_id,
        planner_calls,
    )


def coordinate_verified_terminal_replan(
    value: VerifiedTerminalReplanInput,
    *,
    max_auto_replans: int | None = None,
    planner_pipeline: PlannerPipeline = run_replan_planner,
    persistence_pipeline: PersistencePipeline = persist_replan_result,
) -> RepositoryMultiCycleReplanCoordinatorResult:
    """Coordinate one already-verified terminal event without launching work."""

    try:
        event = _extract_terminal_event(value)
        if not is_auto_replan_eligible(event.reason_code):
            return RepositoryMultiCycleReplanCoordinatorResult(
                "not_eligible",
                "replan.coordinator.not_eligible",
                None,
                event.failed_task_id,
                event.accepted_head_sha,
                None,
                None,
                None,
                0,
            )
        if (
            max_auto_replans is not None
            and (
                isinstance(max_auto_replans, bool)
                or not isinstance(max_auto_replans, int)
                or not 1 <= max_auto_replans <= 8
            )
        ):
            return _blocked("replan.coordinator.budget_invalid")
        if not _SHA256.fullmatch(value.root_queue_spec_sha256) or not _SHA256.fullmatch(
            value.predecessor_queue_spec_sha256
        ):
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.queue_identity_invalid"
            )
        predecessor_path = Path(value.predecessor_queue_spec_path).expanduser()
        if hashlib.sha256(predecessor_path.read_bytes()).hexdigest() != value.predecessor_queue_spec_sha256:
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.predecessor_queue_sha_mismatch"
            )
        predecessor = load_repository_multi_cycle_task_spec(predecessor_path)
        if event.failed_task_index >= len(predecessor.tasks):
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.failed_task_invalid"
            )
        if predecessor.tasks[event.failed_task_index].task_id != event.failed_task_id:
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.failed_task_mismatch"
            )

        attempts = _load_attempts(value)
        for _, _, accepted, _ in attempts:
            if _same_event(accepted, event, value.predecessor_queue_spec_sha256):
                runtime = _rehydrate_runtime(accepted)
                persisted = persistence_pipeline(
                    _persistence_input(value, event, runtime),
                    state_root=value.replan_state_root,
                )
                return _result_from_persistence(persisted, event, 0)

        if attempts and event.cycle_run_id <= attempts[-1][2]["predecessor_cycle_run_id"]:
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.terminal_event_conflict"
            )

        attempt_number = attempts[-1][0] + 1 if attempts else 1
        if max_auto_replans is not None and attempt_number > max_auto_replans:
            return RepositoryMultiCycleReplanCoordinatorResult(
                "blocked",
                "replan.budget_exhausted",
                attempt_number,
                event.failed_task_id,
                event.accepted_head_sha,
                None,
                None,
                None,
                0,
            )
        evidence = ReplanFailureEvidence(
            predecessor,
            event.failed_task_index,
            event.reason_code,
            event.detail_reason_code,
            event.completion_evidence,
            event.accepted_head_sha,
        )
        planner_result = planner_pipeline(
            ReplanPlannerRequest(
                evidence,
                value.source_repository_root,
                event.accepted_head_sha,
                attempt_number,
            )
        )
        if planner_result.status == "blocked":
            return RepositoryMultiCycleReplanCoordinatorResult(
                "blocked",
                planner_result.reason_code,
                attempt_number,
                event.failed_task_id,
                event.accepted_head_sha,
                None,
                None,
                None,
                planner_result.planner_call_count,
            )
        if planner_result.status not in {"successor_ready", "stop"}:
            raise RepositoryMultiCycleReplanCoordinatorError(
                "replan.coordinator.planner_result_invalid"
            )
        persisted = persistence_pipeline(
            _persistence_input(value, event, planner_result),
            state_root=value.replan_state_root,
        )
        return _result_from_persistence(
            persisted, event, planner_result.planner_call_count
        )
    except (OSError, ValueError):
        return _blocked("replan.coordinator.evidence_invalid")


__all__ = [
    "RepositoryMultiCycleReplanCoordinatorResult",
    "VerifiedTerminalReplanInput",
    "coordinate_verified_terminal_replan",
]

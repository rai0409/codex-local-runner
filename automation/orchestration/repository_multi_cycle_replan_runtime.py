"""Disposable, read-only snapshots of an accepted repository commit.

Planner execution is intentionally outside this module. The snapshot is built
solely with local, read-only Git commands and is removed when its context exits.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from automation.orchestration.repository_multi_cycle_replan import (
    ReplanEnvelope,
    ReplanFailureEvidence,
    RepositoryMultiCycleReplanError,
    build_replan_planner_prompt,
    build_successor_queue,
    validate_replan_envelope,
)
from automation.orchestration.repository_multi_cycle_task_spec import (
    RepositoryMultiCycleTaskSpec,
)
from run_codex import run_codex


GIT_TIMEOUT_SECONDS = 20
_ACCEPTED_HEAD_PATTERN = re.compile(r"[0-9a-f]{40}")
GitRunner = Callable[..., subprocess.CompletedProcess[bytes]]
PlannerRunner = Callable[..., Mapping[str, Any]]


class AcceptedHeadSnapshotError(RuntimeError):
    """Fail-closed snapshot error with a stable, non-sensitive reason code."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ReplanPlannerRequest:
    """Inputs required for one isolated planner protocol exchange."""

    evidence: ReplanFailureEvidence
    source_repository_root: str | Path
    accepted_head_sha: str
    replan_attempt_number: int


@dataclass(frozen=True)
class ReplanPlannerResult:
    """In-memory planner and deterministic successor-construction outcome."""

    status: str
    reason_code: str
    replan_attempt_number: int
    validated_envelope: ReplanEnvelope | None
    planner_call_count: int
    replacement_task_id: str | None = None
    successor_queue: RepositoryMultiCycleTaskSpec | None = None
    serialized_successor_queue: str | None = None
    successor_queue_sha256: str | None = None


def _run_git(
    source_repository_root: Path,
    arguments: Sequence[str],
    *,
    git_runner: GitRunner,
    timeout: int,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return git_runner(
            ["git", "-C", str(source_repository_root), *arguments],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcceptedHeadSnapshotError("replan.snapshot.git_failed") from exc


def validate_accepted_head(
    source_repository_root: str | Path,
    accepted_head_sha: str,
    *,
    git_runner: GitRunner = subprocess.run,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> Path:
    """Validate that *accepted_head_sha* is a locally available commit."""

    root = Path(source_repository_root)
    if not root.is_dir():
        raise AcceptedHeadSnapshotError("replan.snapshot.source_not_directory")
    if not isinstance(accepted_head_sha, str) or not _ACCEPTED_HEAD_PATTERN.fullmatch(
        accepted_head_sha
    ):
        raise AcceptedHeadSnapshotError("replan.snapshot.accepted_head_invalid")

    result = _run_git(
        root,
        ("cat-file", "-e", f"{accepted_head_sha}^{{commit}}"),
        git_runner=git_runner,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise AcceptedHeadSnapshotError("replan.snapshot.accepted_head_not_found")
    return root


def validate_archive_members(
    members: Sequence[tarfile.TarInfo], snapshot_root: str | Path
) -> None:
    """Validate every tar member before any member is extracted."""

    root = Path(snapshot_root).resolve()
    for member in members:
        name = member.name
        path = PurePosixPath(name)
        if not name:
            raise AcceptedHeadSnapshotError("replan.snapshot.unsafe_archive")
        if path.is_absolute() or ".." in path.parts:
            raise AcceptedHeadSnapshotError("replan.snapshot.unsafe_archive")
        try:
            root.joinpath(*path.parts).resolve().relative_to(root)
        except ValueError as exc:
            raise AcceptedHeadSnapshotError("replan.snapshot.unsafe_archive") from exc
        if member.issym() or member.islnk():
            raise AcceptedHeadSnapshotError("replan.snapshot.unsafe_archive")
        if not (member.isdir() or member.isreg()):
            raise AcceptedHeadSnapshotError("replan.snapshot.unsafe_archive")


def _extract_archive(archive_payload: bytes, snapshot_root: Path) -> None:
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_payload), mode="r:") as archive:
            members = archive.getmembers()
            validate_archive_members(members, snapshot_root)
            for member in members:
                destination = snapshot_root.joinpath(*PurePosixPath(member.name).parts)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise AcceptedHeadSnapshotError("replan.snapshot.invalid_archive")
                with source, destination.open("wb") as target:
                    shutil.copyfileobj(source, target)
    except AcceptedHeadSnapshotError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise AcceptedHeadSnapshotError("replan.snapshot.invalid_archive") from exc


@contextmanager
def accepted_head_snapshot(
    source_repository_root: str | Path,
    accepted_head_sha: str,
    *,
    git_runner: GitRunner = subprocess.run,
    timeout: int = GIT_TIMEOUT_SECONDS,
) -> Iterator[Path]:
    """Yield an exact disposable snapshot of *accepted_head_sha*."""

    root = validate_accepted_head(
        source_repository_root,
        accepted_head_sha,
        git_runner=git_runner,
        timeout=timeout,
    )
    with tempfile.TemporaryDirectory(prefix="accepted-head-snapshot-") as temporary:
        result = _run_git(
            root,
            ("archive", "--format=tar", accepted_head_sha),
            git_runner=git_runner,
            timeout=timeout,
        )
        if result.returncode != 0:
            raise AcceptedHeadSnapshotError("replan.snapshot.archive_failed")
        snapshot_root = Path(temporary)
        _extract_archive(result.stdout, snapshot_root)
        yield snapshot_root


def _parse_and_validate_planner_output(output: str) -> ReplanEnvelope:
    try:
        value = json.loads(output.strip())
    except (json.JSONDecodeError, TypeError) as exc:
        raise RepositoryMultiCycleReplanError("replan.planner.json_invalid") from exc
    if type(value) is not dict:
        raise RepositoryMultiCycleReplanError("replan.planner.json_object_required")
    return validate_replan_envelope(value)


def _correction_prompt(original_prompt: str, reason_code: str) -> str:
    return (
        original_prompt
        + "\n\nFORMAT CORRECTION: the previous response failed strict validation ("
        + reason_code
        + "). Return exactly one JSON object and nothing else."
    )


def run_replan_planner(
    request: ReplanPlannerRequest,
    *,
    planner: PlannerRunner = run_codex,
) -> ReplanPlannerResult:
    """Run the R6 planner protocol within an accepted-head snapshot."""

    call_count = 0
    if (
        not isinstance(request.replan_attempt_number, int)
        or isinstance(request.replan_attempt_number, bool)
        or not 1 <= request.replan_attempt_number <= 99
    ):
        return ReplanPlannerResult(
            "blocked",
            "replan.attempt.invalid",
            request.replan_attempt_number,
            None,
            call_count,
        )

    original_prompt = build_replan_planner_prompt(request.evidence)
    prompt = original_prompt
    try:
        with accepted_head_snapshot(
            request.source_repository_root, request.accepted_head_sha
        ) as snapshot:
            for attempt in range(2):
                call_count += 1
                try:
                    execution = planner(
                        {"repo_path": str(snapshot)},
                        prompt,
                        work_root=str(snapshot / ".planner-runs"),
                        persist_prompt=False,
                        return_transient_stdout=True,
                    )
                except Exception:
                    return ReplanPlannerResult(
                        "blocked",
                        "replan.planner.execution_failed",
                        request.replan_attempt_number,
                        None,
                        call_count,
                    )
                if (
                    execution.get("status") != "completed"
                    or execution.get("success") is not True
                ):
                    return ReplanPlannerResult(
                        "blocked",
                        "replan.planner.execution_failed",
                        request.replan_attempt_number,
                        None,
                        call_count,
                    )
                output = execution.get("transient_stdout")
                if not isinstance(output, str) or not output.strip():
                    return ReplanPlannerResult(
                        "blocked",
                        "replan.planner.output_missing",
                        request.replan_attempt_number,
                        None,
                        call_count,
                    )
                try:
                    envelope = _parse_and_validate_planner_output(output)
                except RepositoryMultiCycleReplanError as exc:
                    if attempt == 1:
                        return ReplanPlannerResult(
                            "blocked",
                            "replan.planner.protocol_invalid",
                            request.replan_attempt_number,
                            None,
                            call_count,
                        )
                    prompt = _correction_prompt(original_prompt, str(exc))
                    continue
                if envelope.decision == "stop":
                    return ReplanPlannerResult(
                        "stop",
                        "replan.planner.stop",
                        request.replan_attempt_number,
                        None,
                        call_count,
                    )
                try:
                    plan = build_successor_queue(
                        request.evidence,
                        envelope,
                        request.replan_attempt_number,
                    )
                except ValueError:
                    return ReplanPlannerResult(
                        "blocked",
                        "replan.successor.build_failed",
                        request.replan_attempt_number,
                        None,
                        call_count,
                    )
                if (
                    plan.status != "replace_failed_task"
                    or plan.replacement_task is None
                    or plan.successor_queue is None
                    or plan.serialized_successor_queue is None
                    or plan.successor_queue_sha256 is None
                ):
                    return ReplanPlannerResult(
                        "blocked",
                        "replan.successor.build_failed",
                        request.replan_attempt_number,
                        None,
                        call_count,
                    )
                return ReplanPlannerResult(
                    "successor_ready",
                    "replan.successor.ready",
                    request.replan_attempt_number,
                    envelope,
                    call_count,
                    plan.replacement_task.task_id,
                    plan.successor_queue,
                    plan.serialized_successor_queue,
                    plan.successor_queue_sha256,
                )
    except AcceptedHeadSnapshotError as exc:
        return ReplanPlannerResult(
            "blocked",
            exc.reason,
            request.replan_attempt_number,
            None,
            call_count,
        )

    raise AssertionError("bounded planner protocol exhausted without a result")


__all__ = [
    "AcceptedHeadSnapshotError",
    "ReplanPlannerRequest",
    "ReplanPlannerResult",
    "accepted_head_snapshot",
    "run_replan_planner",
    "validate_accepted_head",
    "validate_archive_members",
]

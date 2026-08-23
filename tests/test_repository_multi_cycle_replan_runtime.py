from __future__ import annotations

import json
import subprocess
import tarfile
from pathlib import Path
from typing import Any

import pytest

from automation.orchestration.repository_multi_cycle_replan_runtime import (
    AcceptedHeadSnapshotError,
    ReplanPlannerRequest,
    accepted_head_snapshot,
    run_replan_planner,
    validate_accepted_head,
    validate_archive_members,
)
from automation.orchestration.repository_multi_cycle_replan import ReplanFailureEvidence
from automation.orchestration.repository_multi_cycle_task_spec import (
    validate_repository_multi_cycle_task_spec,
)


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repository), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str, str, bytes]:
    root = tmp_path / "source"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "snapshot@example.invalid")
    _git(root, "config", "user.name", "Snapshot Test")

    (root / "marker.txt").write_text("A", encoding="utf-8")
    _git(root, "add", "marker.txt")
    _git(root, "commit", "-q", "-m", "commit A")
    commit_a = _git(root, "rev-parse", "HEAD").stdout.decode().strip()

    binary = b"\x00\xff\x80\x01binary"
    (root / "marker.txt").write_text("B", encoding="utf-8")
    (root / "binary.dat").write_bytes(binary)
    _git(root, "add", "marker.txt", "binary.dat")
    _git(root, "commit", "-q", "-m", "commit B")
    commit_b = _git(root, "rev-parse", "HEAD").stdout.decode().strip()
    _git(root, "checkout", "-q", commit_a)
    return root, commit_a, commit_b, binary


def test_snapshot_uses_exact_accepted_commit_and_preserves_binary(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, commit_a, commit_b, binary = repository

    with accepted_head_snapshot(root, commit_b) as snapshot:
        assert (snapshot / "marker.txt").read_text(encoding="utf-8") == "B"
        assert (snapshot / "binary.dat").read_bytes() == binary

    assert _git(root, "rev-parse", "HEAD").stdout.decode().strip() == commit_a


def test_source_is_unchanged_and_snapshot_is_disposable(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, _, commit_b, _ = repository
    (root / "untracked.txt").write_text("source", encoding="utf-8")
    branch_before = _git(root, "branch", "--show-current").stdout
    head_before = _git(root, "rev-parse", "HEAD").stdout
    status_before = _git(root, "status", "--porcelain").stdout
    marker_before = (root / "marker.txt").read_bytes()

    with accepted_head_snapshot(root, commit_b) as snapshot:
        snapshot_path = snapshot
        (snapshot / "marker.txt").write_text("snapshot-only", encoding="utf-8")
        (snapshot / "new.txt").write_text("new", encoding="utf-8")
        assert snapshot.exists()

    assert not snapshot_path.exists()
    assert _git(root, "branch", "--show-current").stdout == branch_before
    assert _git(root, "rev-parse", "HEAD").stdout == head_before
    assert _git(root, "status", "--porcelain").stdout == status_before
    assert (root / "marker.txt").read_bytes() == marker_before
    assert (root / "untracked.txt").read_text(encoding="utf-8") == "source"


@pytest.mark.parametrize("accepted_head", ["A" * 40, "a" * 39, "g" * 40])
def test_malformed_sha_fails_before_git(
    tmp_path: Path, accepted_head: str
) -> None:
    calls: list[object] = []

    def runner(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append((args, kwargs))
        raise AssertionError("Git must not run")

    with pytest.raises(AcceptedHeadSnapshotError) as error:
        validate_accepted_head(tmp_path, accepted_head, git_runner=runner)
    assert error.value.reason == "replan.snapshot.accepted_head_invalid"
    assert calls == []


def test_nonexistent_commit_fails_closed(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, _, _, _ = repository
    with pytest.raises(AcceptedHeadSnapshotError) as error:
        validate_accepted_head(root, "0" * 40)
    assert error.value.reason == "replan.snapshot.accepted_head_not_found"


def _member(name: str, member_type: bytes = tarfile.REGTYPE) -> tarfile.TarInfo:
    value = tarfile.TarInfo(name)
    value.type = member_type
    return value


@pytest.mark.parametrize(
    "member",
    [
        _member("../../outside"),
        _member("/tmp/outside"),
        _member("link", tarfile.SYMTYPE),
        _member("link", tarfile.LNKTYPE),
        _member("fifo", tarfile.FIFOTYPE),
    ],
    ids=["traversal", "absolute", "symlink", "hardlink", "special"],
)
def test_unsafe_archive_member_is_rejected(tmp_path: Path, member: tarfile.TarInfo) -> None:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    outside = tmp_path / "outside"

    with pytest.raises(AcceptedHeadSnapshotError) as error:
        validate_archive_members([member], snapshot)

    assert error.value.reason == "replan.snapshot.unsafe_archive"
    assert not outside.exists()


def test_snapshot_cleanup_on_exception(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, _, commit_b, _ = repository
    snapshot_path: Path | None = None

    with pytest.raises(RuntimeError, match="downstream failure"):
        with accepted_head_snapshot(root, commit_b) as snapshot:
            snapshot_path = snapshot
            raise RuntimeError("downstream failure")

    assert snapshot_path is not None
    assert not snapshot_path.exists()


def test_snapshot_runs_only_cat_file_and_archive(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, _, commit_b, _ = repository
    invocations: list[list[str]] = []

    def recording_runner(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[bytes]:
        invocations.append(command)
        assert kwargs["shell"] is False
        assert kwargs["stdin"] is subprocess.DEVNULL
        assert "timeout" in kwargs
        return subprocess.run(command, **kwargs)  # type: ignore[arg-type]

    with accepted_head_snapshot(root, commit_b, git_runner=recording_runner):
        pass

    assert [command[3] for command in invocations] == ["cat-file", "archive"]
    forbidden = {
        "checkout",
        "switch",
        "reset",
        "restore",
        "worktree",
        "branch",
        "update-ref",
    }
    assert not any(forbidden.intersection(command[3:]) for command in invocations)


def _evidence() -> ReplanFailureEvidence:
    queue = validate_repository_multi_cycle_task_spec(
        {
            "schema_version": "1",
            "tasks": [
                {
                    "task_id": "failed",
                    "prompt": "original",
                    "allowed_changed_paths": ["marker.txt"],
                    "commit_message": "Original",
                }
            ],
        }
    )
    return ReplanFailureEvidence(
        queue,
        0,
        "single_task.task_completion.rework_exhausted",
        "contract.missing",
        {"reason_code": "contract.missing", "raw_log": "SECRET"},
    )


def _request(
    repository: tuple[Path, str, str, bytes]
) -> ReplanPlannerRequest:
    root, _, commit_b, _ = repository
    return ReplanPlannerRequest(_evidence(), root, commit_b, 1)


def _replacement(**extra: Any) -> str:
    value = {
        "schema_version": "1",
        "decision": "replace_failed_task",
        "prompt": "repair the failure",
        "allowed_changed_paths": ["marker.txt"],
        "commit_message": "Repair failure",
        **extra,
    }
    return json.dumps(value)


class _Planner:
    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[dict[str, Any], str, dict[str, Any]]] = []

    def __call__(
        self, task: dict[str, Any], prompt: str, **kwargs: Any
    ) -> dict[str, Any]:
        self.calls.append((task, prompt, kwargs))
        return self.outputs[len(self.calls) - 1]


def _completed(output: str) -> dict[str, Any]:
    return {"status": "completed", "success": True, "transient_stdout": output}


def test_planner_uses_disposable_snapshot_and_r3_options(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, _, _, _ = repository
    planner = _Planner([_completed(_replacement())])

    result = run_replan_planner(_request(repository), planner=planner)

    task, _, options = planner.calls[0]
    planner_path = Path(task["repo_path"])
    assert result.status == "replacement_envelope_ready"
    assert result.planner_call_count == 1
    assert result.validated_envelope is not None
    assert result.validated_envelope.decision == "replace_failed_task"
    assert planner_path != root
    assert not planner_path.exists()
    assert options["persist_prompt"] is False
    assert options["return_transient_stdout"] is True
    assert Path(options["work_root"]).is_relative_to(planner_path)


def test_valid_stop_returns_without_envelope(
    repository: tuple[Path, str, str, bytes],
) -> None:
    planner = _Planner([_completed('{"schema_version":"1","decision":"stop"}')])

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "stop"
    assert result.validated_envelope is None
    assert result.planner_call_count == 1


@pytest.mark.parametrize(
    "invalid",
    [
        'Here is the result:\n{"schema_version":"1","decision":"stop"}',
        '```json\n{"schema_version":"1","decision":"stop"}\n```',
    ],
    ids=["prose", "fenced"],
)
def test_non_whole_json_requires_one_correction_retry(
    repository: tuple[Path, str, str, bytes], invalid: str
) -> None:
    planner = _Planner(
        [_completed(invalid), _completed('{"schema_version":"1","decision":"stop"}')]
    )

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "stop"
    assert result.planner_call_count == 2
    assert "Return exactly one JSON object and nothing else" in planner.calls[1][1]
    assert invalid not in planner.calls[1][1]


def test_malformed_twice_is_blocked_after_two_calls(
    repository: tuple[Path, str, str, bytes],
) -> None:
    planner = _Planner([_completed("not json"), _completed("still not json")])

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "blocked"
    assert result.reason_code == "replan.planner.protocol_invalid"
    assert result.planner_call_count == 2


def test_r6a_unknown_authority_field_is_rejected(
    repository: tuple[Path, str, str, bytes],
) -> None:
    planner = _Planner([_completed(_replacement(task_id="model")), _completed("invalid")])

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "blocked"
    assert result.planner_call_count == 2


@pytest.mark.parametrize("status", ["failed", "timed_out", "not_started"])
def test_unsuccessful_execution_has_no_retry(
    repository: tuple[Path, str, str, bytes], status: str
) -> None:
    planner = _Planner([{"status": status, "success": False}])

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "blocked"
    assert result.reason_code == "replan.planner.execution_failed"
    assert result.planner_call_count == 1
    assert len(planner.calls) == 1


@pytest.mark.parametrize(
    "execution",
    [
        {"status": "completed", "success": True},
        {"status": "completed", "success": True, "transient_stdout": "   "},
        {"status": "completed", "success": True, "transient_stdout": None},
    ],
)
def test_missing_transient_stdout_has_no_retry(
    repository: tuple[Path, str, str, bytes], execution: dict[str, Any]
) -> None:
    planner = _Planner([execution])

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "blocked"
    assert result.reason_code == "replan.planner.output_missing"
    assert result.planner_call_count == 1


def test_invalid_envelope_then_valid_replacement_succeeds(
    repository: tuple[Path, str, str, bytes],
) -> None:
    invalid = json.dumps({"schema_version": "1", "decision": "replace_failed_task"})
    planner = _Planner([_completed(invalid), _completed(_replacement())])

    result = run_replan_planner(_request(repository), planner=planner)

    assert result.status == "replacement_envelope_ready"
    assert result.validated_envelope is not None
    assert result.planner_call_count == 2


def test_planner_writes_are_discarded_and_source_is_immutable(
    repository: tuple[Path, str, str, bytes],
) -> None:
    root, _, _, _ = repository
    branch_before = _git(root, "branch", "--show-current").stdout
    head_before = _git(root, "rev-parse", "HEAD").stdout
    status_before = _git(root, "status", "--porcelain").stdout
    snapshot_paths: list[Path] = []

    def writing_planner(
        task: dict[str, Any], prompt: str, **kwargs: Any
    ) -> dict[str, Any]:
        del prompt, kwargs
        snapshot = Path(task["repo_path"])
        snapshot_paths.append(snapshot)
        (snapshot / "planner-created.txt").write_text("temporary", encoding="utf-8")
        return _completed(_replacement())

    result = run_replan_planner(_request(repository), planner=writing_planner)

    assert result.status == "replacement_envelope_ready"
    assert snapshot_paths and not snapshot_paths[0].exists()
    assert not (root / "planner-created.txt").exists()
    assert _git(root, "branch", "--show-current").stdout == branch_before
    assert _git(root, "rev-parse", "HEAD").stdout == head_before
    assert _git(root, "status", "--porcelain").stdout == status_before

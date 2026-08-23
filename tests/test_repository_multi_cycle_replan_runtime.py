from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

import pytest

from automation.orchestration.repository_multi_cycle_replan_runtime import (
    AcceptedHeadSnapshotError,
    accepted_head_snapshot,
    validate_accepted_head,
    validate_archive_members,
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

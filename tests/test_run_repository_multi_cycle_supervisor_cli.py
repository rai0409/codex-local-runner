from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest


def _cli_module():
    path = Path(__file__).resolve().parents[1] / "scripts/run_repository_multi_cycle_supervisor.py"
    spec = importlib.util.spec_from_file_location("r6c2a_supervisor_cli", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _result():
    return SimpleNamespace(
        status="completed",
        reason_code="supervisor.shutdown",
        repository_id="repo",
        queue_sha256=None,
        cycle_run_id=None,
        crash_restart_count=0,
    )


def _run(cli, arguments: list[str]):
    captured: list[dict[str, object]] = []

    class FakeSupervisor:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs)

        def request_shutdown(self, *args):
            return None

        def run_forever(self):
            return _result()

    with (
        mock.patch.object(cli, "RepositoryMultiCycleSupervisor", FakeSupervisor),
        mock.patch.object(cli.signal, "signal"),
    ):
        assert cli.main(["--repository-id", "repo", "--queue-spec", "queue", *arguments]) == 0
    return captured[0]


def test_cli_default_and_max_without_auto_leave_coordinator_disabled() -> None:
    cli = _cli_module()

    default = _run(cli, [])
    max_only = _run(cli, ["--max-auto-replans", "1"])

    assert default.get("replan_coordinator") is None
    assert max_only.get("replan_coordinator") is None
    assert default.get("auto_replan_launch") is None
    assert max_only.get("auto_replan_launch") is None


@pytest.mark.parametrize(("arguments", "expected"), [(["--auto-replan"], 2), (["--auto-replan", "--max-auto-replans", "1"], 1)])
def test_cli_auto_replan_forwards_budget(arguments: list[str], expected: int) -> None:
    cli = _cli_module()
    sentinel = object()
    with mock.patch.object(cli, "coordinate_verified_terminal_replan", return_value="ready") as coordinator:
        kwargs = _run(cli, arguments)
        wrapper = kwargs["replan_coordinator"]
        assert callable(wrapper)
        assert wrapper(sentinel) == "ready"
    coordinator.assert_called_once_with(sentinel, max_auto_replans=expected)
    assert kwargs["auto_replan_launch"] is True


@pytest.mark.parametrize("value", ["0", "-1", "9"])
def test_cli_rejects_invalid_budget_before_supervisor(value: str) -> None:
    cli = _cli_module()
    with mock.patch.object(cli, "RepositoryMultiCycleSupervisor") as supervisor:
        with pytest.raises(SystemExit) as exc:
            cli.main([
                "--repository-id", "repo", "--queue-spec", "queue",
                "--max-auto-replans", value,
            ])
    assert exc.value.code == 2
    supervisor.assert_not_called()


def test_successor_ready_hook_does_not_launch_an_additional_worker() -> None:
    cli = _cli_module()
    calls = []

    class FakeSupervisor:
        def __init__(self, *args, **kwargs):
            calls.append(kwargs["replan_coordinator"](object()))

        def request_shutdown(self, *args):
            return None

        def run_forever(self):
            return _result()

    with (
        mock.patch.object(cli, "RepositoryMultiCycleSupervisor", FakeSupervisor),
        mock.patch.object(cli, "coordinate_verified_terminal_replan", return_value=SimpleNamespace(status="successor_ready")),
        mock.patch.object(cli.signal, "signal"),
        mock.patch("subprocess.Popen") as popen,
    ):
        assert cli.main(["--repository-id", "repo", "--queue-spec", "queue", "--auto-replan"]) == 0

    assert calls[0].status == "successor_ready"
    popen.assert_not_called()

"""Synthetic real-Git acceptance coverage for the complete R6 auto-replan path."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from automation.orchestration.repository_multi_cycle_replan_coordinator import (
    coordinate_verified_terminal_replan,
)
from automation.orchestration.repository_multi_cycle_replan_launch import (
    ReplanLaunchClaimInput,
    load_verified_replan_launch_claim,
)
from automation.orchestration.repository_multi_cycle_replan_launch_execution import (
    ReplanLaunchExecutionInput,
    load_verified_replan_launch_execution,
)
from automation.orchestration.repository_multi_cycle_replan_state import (
    ReplanPersistenceResult,
    load_verified_accepted_replan,
    load_verified_campaign_state,
)
from automation.orchestration.repository_multi_cycle_replan_runtime import (
    run_replan_planner,
)
from automation.orchestration.repository_multi_cycle_supervisor import (
    RepositoryMultiCycleSupervisor,
)
from automation.orchestration.repository_multi_cycle_state import load_latest_checkpoint
from automation.orchestration.repository_multi_cycle_task_executor import (
    run_repository_multi_cycle,
)
from automation.orchestration.repository_multi_cycle_task_spec import (
    load_repository_multi_cycle_task_spec,
)
from automation.orchestration.repository_profile import (
    APPROVAL_ACTIONS,
    FORBIDDEN_GIT_OPERATION_IDS,
)


PYTHON = str(Path(sys.executable).resolve())


def git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )


class FixtureAdapter:
    """The normal single-task adapter seam, with real Git acceptance retained."""

    name = "codex_cli"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def execute_prepared_worktree(self, payload: dict[str, object]) -> dict[str, object]:
        prompt = str(payload["prompt"])
        self.prompts.append(prompt)
        root = Path(str(payload["worktree_path"]))
        if prompt == "make predecessor":
            (root / "predecessor.txt").write_text("B\n", encoding="utf-8")
        elif prompt == "make successor":
            (root / "successor.txt").write_text("C\n", encoding="utf-8")
        elif prompt == "force rework":
            (root / "successor.txt").write_text("needs rework\n", encoding="utf-8")
        elif prompt.startswith("Mode: Repair\n"):
            pass
        else:
            raise AssertionError(f"unexpected task prompt: {prompt!r}")
        return {
            "status": "completed",
            "verify": {
                "status": "passed",
                "reason": "validation_passed",
                "safe_validation": {"status": "passed"},
            },
            "retry": {"attempted": False, "outcome": "not_attempted"},
        }


class SyntheticWorker:
    def __init__(self, pid: int, run: callable) -> None:  # type: ignore[valid-type]
        self.pid = pid
        self._run = run
        self.result = None

    def wait(self) -> int:
        if self.result is None:
            self.result = self._run()
        return 0


def _completion_output(work_root: str, number: int, value: dict[str, object]) -> dict[str, str]:
    directory = Path(work_root) / f"fixture-evaluation-{number}"
    directory.mkdir(parents=True, exist_ok=True)
    stdout = directory / "stdout.txt"
    payload = (
        "TASK_COMPLETION_EVALUATION_JSON_BEGIN\n"
        + json.dumps(value, ensure_ascii=True, sort_keys=True)
        + "\nTASK_COMPLETION_EVALUATION_JSON_END\n"
    )
    stdout.write_text(payload, encoding="utf-8")
    return {
        "status": "completed",
        "stdout_path": str(stdout),
        "transient_stdout": payload,
    }


def _sidecar_digest(path: Path) -> str:
    sidecar = path.with_suffix(".sha256").read_text(encoding="ascii")
    expected = f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
    assert sidecar == expected
    return expected.split(" ", 1)[0]


def test_real_git_r6_auto_replan_launches_one_r5_continued_successor() -> None:
    """Exercise R6-C2b2b end-to-end without a live planner/model request."""

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "configured-source"
        source.mkdir()
        git(source, "init", "-b", "main")
        git(source, "config", "user.name", "R6 acceptance")
        git(source, "config", "user.email", "r6@example.invalid")
        (source / "base.txt").write_text("A\n", encoding="utf-8")
        git(source, "add", "--", "base.txt")
        git(source, "commit", "-m", "A")
        source_branch = git(source, "branch", "--show-current").stdout.strip()
        a = git(source, "rev-parse", "HEAD").stdout.strip()
        source_status = git(source, "status", "--porcelain").stdout

        commands = [
            {
                "command_id": kind,
                "kind": kind,
                    "argv": ["git", "diff", "--check"],
                "cwd": ".",
                "timeout_seconds": 30,
                "required": True,
                "stop_on_failure": True,
            }
            for kind in ("focused", "related_regression", "full", "compile")
        ] + [
            {
                "command_id": "diff",
                "kind": "diff_check",
                "argv": ["git", "diff", "--check"],
                "cwd": ".",
                "timeout_seconds": 30,
                "required": True,
                "stop_on_failure": True,
            }
        ]
        profile = root / "profile.json"
        profile.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "profile_id": "repo",
                    "repository_root": str(source),
                    "base_branch": "main",
                    "python_executable": PYTHON,
                    "validation_commands": commands,
                    "artifact_requirements": [],
                    "forbidden_git_operations": list(FORBIDDEN_GIT_OPERATION_IDS),
                    "max_changed_files": 1,
                    "approval_boundary": {
                        item: "automatic" for item in APPROVAL_ACTIONS
                    },
                    "environment_allowlist": [],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        registry = root / "repositories.json"
        registry.write_text(
            json.dumps({"version": 1, "repos": [{"name": "repo", "logical_role": "fixture"}]}),
            encoding="utf-8",
        )
        bindings = root / "bindings.json"
        bindings.write_text(
            json.dumps(
                {
                    "version": 1,
                    "bindings": [{"repository_id": "repo", "profile_path": str(profile)}],
                }
            ),
            encoding="utf-8",
        )
        predecessor_queue = root / "predecessor-queue.json"
        predecessor_queue.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "tasks": [
                        {
                            "task_id": "accepted-prefix",
                            "prompt": "make predecessor",
                            "allowed_changed_paths": ["predecessor.txt"],
                            "commit_message": "B",
                        },
                        {
                            "task_id": "failed-task",
                            "prompt": "force rework",
                            "allowed_changed_paths": ["successor.txt"],
                            "commit_message": "replacement",
                            "execution_timeout_seconds": 1201,
                            "validation_timeout_seconds": 1202,
                            "completion_evaluator_timeout_seconds": 1203,
                            "completion_rework_timeout_seconds": 1204,
                        },
                    ],
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        cycles = root / "cycles"
        child_runs = root / "single-task-runs"

        predecessor_adapter = FixtureAdapter()
        predecessor_evaluations = 0

        def predecessor_evaluator(**kwargs: object) -> dict[str, str]:
            nonlocal predecessor_evaluations
            predecessor_evaluations += 1
            prompt = str(kwargs["prompt"])
            if "Original human-authored task:\nmake predecessor" in prompt:
                evaluation = {
                    "status": "completed",
                    "reason_code": "fixture.completed",
                    "satisfied_criteria": ["fixture"],
                    "unsatisfied_criteria": [],
                    "evidence_refs": ["fixture"],
                }
            else:
                evaluation = {
                    "status": "needs_rework",
                    "reason_code": "fixture.requires_rework",
                    "satisfied_criteria": [],
                    "unsatisfied_criteria": ["fixture"],
                    "evidence_refs": ["fixture"],
                }
            return _completion_output(str(kwargs["work_root"]), predecessor_evaluations, evaluation)

        predecessor = run_repository_multi_cycle(
            "repo",
            predecessor_queue,
            registry_path=registry,
            bindings_path=bindings,
            output_root=cycles,
            single_task_output_root=child_runs,
            adapter_resolver=lambda: predecessor_adapter,
            evaluator_runner=predecessor_evaluator,
        )
        assert predecessor.status == "blocked", predecessor.reason_code
        assert predecessor.reason_code == "multi_cycle.child.blocked"
        predecessor_receipt = json.loads(Path(predecessor.receipt_path).read_text(encoding="utf-8"))
        terminal_state, _ = load_latest_checkpoint(
            cycles / predecessor.cycle_run_id / "state"
        )
        assert terminal_state["terminal_task_result"]["reason_code"] == (
            "single_task.task_completion.rework_exhausted"
        )
        child_receipts = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in child_runs.rglob("receipt.json")
        ]
        failed_child = next(
            value for value in child_receipts if value["task_id"] == "failed-task"
        )
        assert failed_child["reason_code"] == "single_task.task_completion.rework_exhausted"
        assert failed_child["actual_changed_files"] == ["successor.txt"]
        assert failed_child["declared_allowed_changed_paths"] == ["successor.txt"]
        assert failed_child["original_unexpected_changed_files"] == []
        assert failed_child["effective_allowed_changed_paths"] == ["successor.txt"]
        assert failed_child["auto_expanded_paths"] == []
        assert failed_child["scope_recovery_status"] == "not_needed"
        failed_attempts = json.loads(
            Path(failed_child["artifact_paths"]["task_completion_attempts"]).read_text(
                encoding="utf-8"
            )
        )["attempts"]
        assert [attempt["status"] for attempt in failed_attempts] == [
            "needs_rework",
            "needs_rework",
            "needs_rework",
        ]
        assert [attempt["rework_attempted"] for attempt in failed_attempts] == [
            True,
            True,
            False,
        ]
        b = predecessor.accepted_head_sha
        assert b is not None and b != a, (
            predecessor_receipt,
            predecessor_adapter.prompts,
            child_receipts,
        )
        assert predecessor_receipt["final_accepted_head_sha"] == b
        assert predecessor_receipt["executed_task_results"][0]["commit_sha"] == b
        assert predecessor_receipt["stopped_task_id"] == "failed-task"
        predecessor_directory = cycles / predecessor.cycle_run_id
        predecessor_authority = {
            path: path.read_bytes()
            for path in (
                predecessor_directory / "receipt.json",
                predecessor_directory / "receipt.sha256",
                *sorted((predecessor_directory / "state").iterdir()),
            )
        }

        planner_calls: list[dict[str, object]] = []

        def fake_external_planner(
            repository: dict[str, object], prompt: str, **kwargs: object
        ) -> dict[str, object]:
            planner_calls.append({"repository": repository, "prompt": prompt, **kwargs})
            snapshot = Path(str(repository["repo_path"]))
            assert snapshot != source
            assert (snapshot / "predecessor.txt").read_text(encoding="utf-8") == "B\n"
            return {
                "status": "completed",
                "success": True,
                "transient_stdout": json.dumps(
                    {
                        "schema_version": "1",
                        "decision": "replace_failed_task",
                        "prompt": "make successor",
                        "allowed_changed_paths": ["successor.txt"],
                        "commit_message": "C",
                    },
                    sort_keys=True,
                ),
            }

        replan_state = root / "replan-state"
        coordinator_inputs = []

        def production_coordinator(value: object):
            coordinator_inputs.append(value)
            return coordinate_verified_terminal_replan(
                replace(value, replan_state_root=replan_state),  # type: ignore[arg-type]
                max_auto_replans=2,
                planner_pipeline=lambda request: run_replan_planner(
                    request, planner=fake_external_planner
                ),
            )

        successor_runs = []
        successor_adapter = FixtureAdapter()
        successor_evaluations = 0
        selected_queues: list[Path] = []
        worker_launch_count = 0
        supervisor: RepositoryMultiCycleSupervisor

        def successor_evaluator(**kwargs: object) -> dict[str, str]:
            nonlocal successor_evaluations
            successor_evaluations += 1
            assert "Original human-authored task:\nmake successor" in str(kwargs["prompt"])
            return _completion_output(
                str(kwargs["work_root"]),
                successor_evaluations,
                {
                    "status": "completed",
                    "reason_code": "fixture.completed",
                    "satisfied_criteria": ["fixture"],
                    "unsatisfied_criteria": [],
                    "evidence_refs": ["fixture"],
                },
            )

        def worker_factory(resume_cycle_run_id: str | None) -> SyntheticWorker:
            nonlocal worker_launch_count
            assert resume_cycle_run_id is None
            worker_launch_count += 1
            assert selected_queues
            queue_path = selected_queues[-1]

            def execute_successor():
                result = run_repository_multi_cycle(
                    "repo",
                    queue_path,
                    registry_path=registry,
                    bindings_path=bindings,
                    output_root=cycles,
                    single_task_output_root=child_runs,
                    adapter_resolver=lambda: successor_adapter,
                    evaluator_runner=successor_evaluator,
                )
                successor_runs.append(result)
                return result

            return SyntheticWorker(43121, execute_successor)

        def stop_after_terminal_idle(_: float) -> None:
            supervisor.request_shutdown()

        supervisor = RepositoryMultiCycleSupervisor(
            "repo",
            predecessor_queue,
            state_root=root / "supervisor-state",
            cycle_output_root=cycles,
            registry_path=registry,
            bindings_path=bindings,
            single_task_output_root=child_runs,
            poll_seconds=0,
            worker_factory=worker_factory,
            sleep=stop_after_terminal_idle,
            replan_coordinator=production_coordinator,
            auto_replan_launch=True,
        )
        original_launch = supervisor._launch

        def observe_existing_launch_helper(
            resume_cycle_run_id: str | None, *, queue_spec_path: Path | None = None
        ) -> object:
            assert queue_spec_path is not None
            selected_queues.append(queue_spec_path)
            return original_launch(resume_cycle_run_id, queue_spec_path=queue_spec_path)

        supervisor._launch = observe_existing_launch_helper  # type: ignore[method-assign]
        supervisor_result = supervisor.run_forever()
        assert supervisor_result.status == "completed"
        assert len(coordinator_inputs) == 1
        assert len(planner_calls) == 1  # one R6 attempt, not a live Codex call
        assert worker_launch_count == 1
        assert len(successor_runs) == 1
        successor = successor_runs[0]
        assert successor.status == "completed"
        c = successor.accepted_head_sha
        assert c is not None and c != b

        replan = supervisor._last_replan_result
        assert replan is not None and replan.status == "successor_ready"
        assert replan.replan_attempt_number == 1
        assert replan.successor_queue_path is not None
        assert replan.successor_queue_sha256 is not None
        assert selected_queues == [replan.successor_queue_path]
        assert supervisor._last_replan_launch_result is not None
        assert supervisor._last_replan_launch_result.status == "launched"
        assert supervisor._last_replan_launch_result.worker_pid == 43121

        attempt = replan.successor_queue_path.parent
        accepted = load_verified_accepted_replan(attempt)
        campaign = load_verified_campaign_state(attempt)
        assert accepted["decision"] == "replace_failed_task"
        assert accepted["accepted_head_sha"] == b
        assert campaign["state"] == "successor_ready"
        assert _sidecar_digest(attempt / "accepted_replan.json")
        assert _sidecar_digest(replan.successor_queue_path) == replan.successor_queue_sha256
        assert _sidecar_digest(attempt / "campaign.json")
        successor_queue = load_repository_multi_cycle_task_spec(replan.successor_queue_path)
        assert [task.task_id for task in successor_queue.tasks] == ["failed-task-replan-1"]
        replacement = successor_queue.tasks[0]
        assert replacement.prompt == "make successor"
        assert replacement.execution_timeout_seconds == 1201
        assert replacement.validation_timeout_seconds == 1202
        assert replacement.completion_evaluator_timeout_seconds == 1203
        assert replacement.completion_rework_timeout_seconds == 1204

        persisted = ReplanPersistenceResult(
            "successor_ready",
            "replan.persistence.ready",
            replan.campaign_id,
            attempt,
            attempt / "accepted_replan.json",
            replan.successor_queue_path,
            replan.successor_queue_sha256,
            attempt / "campaign.json",
            1,
            replacement.task_id,
        )
        claim_input = ReplanLaunchClaimInput(persisted, "repo", b)
        claim = load_verified_replan_launch_claim(claim_input)
        assert claim.status == "launch_pending"
        assert claim.claim_path is not None and claim.launch_id is not None
        assert _sidecar_digest(claim.claim_path)
        execution = load_verified_replan_launch_execution(
            ReplanLaunchExecutionInput(claim_input, claim)
        )
        assert execution.status == "launched"
        assert execution.launch_id == claim.launch_id
        assert execution.worker_pid == 43121
        assert execution.execution_path is not None
        assert _sidecar_digest(execution.execution_path)

        assert git(source, "cat-file", "-e", f"{a}^{{commit}}")
        assert git(source, "cat-file", "-e", f"{b}^{{commit}}")
        assert git(source, "cat-file", "-e", f"{c}^{{commit}}")
        assert git(source, "merge-base", "--is-ancestor", a, b).returncode == 0
        assert git(source, "merge-base", "--is-ancestor", b, c).returncode == 0
        successor_receipt = json.loads(Path(successor.receipt_path).read_text(encoding="utf-8"))
        assert successor_receipt["continuation_base_sha"] == b
        assert successor_receipt["final_accepted_head_sha"] == c
        assert git(source, "branch", "--show-current").stdout.strip() == source_branch
        assert git(source, "rev-parse", "HEAD").stdout.strip() == a
        assert git(source, "status", "--porcelain").stdout == source_status
        assert {path: path.read_bytes() for path in predecessor_authority} == predecessor_authority

        replay_launches = worker_launch_count
        replay_planner_calls = len(planner_calls)
        replay_attempts = sorted(replan_state.rglob("attempt-*"))
        fresh = RepositoryMultiCycleSupervisor(
            "repo",
            predecessor_queue,
            state_root=root / "fresh-supervisor-state",
            cycle_output_root=cycles,
            registry_path=registry,
            bindings_path=bindings,
            single_task_output_root=child_runs,
            worker_factory=lambda _: (_ for _ in ()).throw(AssertionError("relaunch")),
            sleep=lambda _: None,
            replan_coordinator=production_coordinator,
            auto_replan_launch=True,
        )
        replay = fresh.run_once()
        assert replay.status == "idle"
        assert replay.replan_result is not None
        assert replay.replan_result.status == "successor_ready"
        assert len(planner_calls) == replay_planner_calls
        assert worker_launch_count == replay_launches
        assert sorted(replan_state.rglob("attempt-*")) == replay_attempts
        assert load_verified_replan_launch_claim(claim_input).launch_id == claim.launch_id
        print(f"R6 real-Git evidence: A={a} B={b} C={c} launch_id={claim.launch_id}")

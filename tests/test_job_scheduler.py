from __future__ import annotations

from datetime import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from automation.scheduler.job_registry import FileJobRegistry
from automation.scheduler.job_registry import STATE_ESCALATED
from automation.scheduler.job_registry import STATE_FAILED_TERMINAL
from automation.scheduler.job_registry import STATE_PAUSED
from automation.scheduler.job_registry import STATE_PENDING
from automation.scheduler.job_registry import STATE_RETRY_SCHEDULED
from automation.scheduler.job_scheduler import JobScheduler
from automation.scheduler.job_scheduler import SchedulerJob


class _FakeDispatcher:
    def __init__(self, responses: dict[str, dict[str, object]] | None = None) -> None:
        self.responses = dict(responses or {})
        self.requests: list[object] = []

    def dispatch_once(self, request):
        self.requests.append(request)
        payload = self.responses.get(
            str(request.job_id),
            {
                "job_id": request.job_id,
                "dispatch_status": "executed",
                "audit": {
                    "routing_reason": "executor_succeeded",
                    "whether_human_required": False,
                },
            },
        )
        return dict(payload)


class JobSchedulerTests(unittest.TestCase):
    def _fixed_now(self) -> datetime:
        return datetime(2026, 4, 18, 14, 0, 0)

    def _write_planning_dir(self, root: Path, name: str) -> Path:
        planning_dir = root / name
        planning_dir.mkdir(parents=True, exist_ok=True)
        (planning_dir / "project_brief.json").write_text(
            json.dumps({"project_id": name, "target_repo": "acme/repo"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (planning_dir / "repo_facts.json").write_text(
            json.dumps({"repo": "acme/repo", "default_branch": "main"}, ensure_ascii=False),
            encoding="utf-8",
        )
        (planning_dir / "roadmap.json").write_text(json.dumps({"roadmap_id": name}), encoding="utf-8")
        (planning_dir / "pr_plan.json").write_text(
            json.dumps(
                {
                    "plan_id": name,
                    "prs": [
                        {
                            "pr_id": "pr-1",
                            "title": "slice",
                            "exact_scope": "scope",
                            "touched_files": ["README.md"],
                            "forbidden_files": [],
                            "acceptance_criteria": ["ok"],
                            "validation_commands": ["python3 -m unittest"],
                            "rollback_notes": "none",
                            "tier_category": "docs_only",
                            "depends_on": [],
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return planning_dir

    def test_discover_pending_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            pending = self._write_planning_dir(artifacts_root, "job-pending")
            self._write_planning_dir(artifacts_root, "job-completed")
            (output_root / "job-completed").mkdir(parents=True, exist_ok=True)
            (output_root / "job-completed" / "manifest.json").write_text("{}", encoding="utf-8")

            scheduler = JobScheduler(dispatcher=_FakeDispatcher())
            jobs = scheduler.discover_pending_jobs(
                artifacts_root=artifacts_root,
                output_root=output_root,
                dry_run=False,
                max_retry_dispatches=1,
            )

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "job-pending")
        self.assertEqual(Path(jobs[0].artifacts_input_dir), pending)
        self.assertEqual(Path(jobs[0].output_dir), output_root)
        self.assertFalse(jobs[0].dry_run)

    def test_run_cycle_dispatches_explicit_jobs(self) -> None:
        dispatcher = _FakeDispatcher()
        scheduler = JobScheduler(dispatcher=dispatcher)
        jobs = [
            SchedulerJob(
                job_id="job-1",
                artifacts_input_dir="/tmp/job-1/planning",
                output_dir="/tmp/job-1/executions",
                dry_run=True,
                write_authority={"state": "write_allowed", "write_actions_allowed": True},
            ),
            SchedulerJob(
                job_id="job-2",
                artifacts_input_dir="/tmp/job-2/planning",
                output_dir="/tmp/job-2/executions",
                dry_run=False,
                pr_number=42,
            ),
        ]
        results = scheduler.run_cycle(jobs)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["job_id"], "job-1")
        self.assertEqual(results[1]["job_id"], "job-2")
        self.assertEqual(len(dispatcher.requests), 2)
        self.assertEqual(dispatcher.requests[1].pr_number, 42)
        self.assertEqual(dispatcher.requests[0].dry_run, True)
        self.assertEqual(dispatcher.requests[1].dry_run, False)

    def test_discover_pending_jobs_ignores_invalid_artifact_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            valid = self._write_planning_dir(artifacts_root, "job-valid")
            invalid = artifacts_root / "job-invalid"
            invalid.mkdir(parents=True, exist_ok=True)
            (invalid / "project_brief.json").write_text(json.dumps({}), encoding="utf-8")

            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now)
            jobs = scheduler.discover_pending_jobs(
                artifacts_root=artifacts_root,
                output_root=output_root,
            )

        self.assertEqual(len(jobs), 1)
        self.assertEqual(Path(jobs[0].artifacts_input_dir), valid)

    def test_discover_pending_jobs_skips_paused_jobs_not_yet_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-paused")
            run_root = output_root / "job-paused"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "manifest.json").write_text("{}", encoding="utf-8")
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-paused",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_rate_limit_reset",
                        "pause_reason": "rate limit",
                        "next_eligible_at": "2026-04-18T15:00:00",
                        "updated_at": "2026-04-18T14:00:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now)
            jobs = scheduler.discover_pending_jobs(artifacts_root=artifacts_root, output_root=output_root)

        self.assertEqual(jobs, [])

    def test_discover_pending_jobs_includes_paused_jobs_when_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            paused_planning = self._write_planning_dir(artifacts_root, "job-paused")
            run_root = output_root / "job-paused"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "manifest.json").write_text("{}", encoding="utf-8")
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-paused",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_checks",
                        "pause_reason": "checks pending",
                        "next_eligible_at": "2026-04-18T13:30:00",
                        "updated_at": "2026-04-18T13:00:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )

            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now)
            jobs = scheduler.discover_pending_jobs(artifacts_root=artifacts_root, output_root=output_root)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_id, "job-paused")
        self.assertEqual(Path(jobs[0].artifacts_input_dir), paused_planning)

    def test_pending_to_runnable_transition_via_registry_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-1")

            registry = FileJobRegistry(output_root / "job_registry.json", now=self._fixed_now)
            registry.upsert({"job_id": "job-1", "current_state": STATE_PENDING})

            run_root = output_root / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "manifest.json").write_text("{}", encoding="utf-8")

            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now, registry=registry)
            records = scheduler.sync_registry_from_artifacts(artifacts_root=artifacts_root, output_root=output_root)

        record = next(item for item in records if item["job_id"] == "job-1")
        self.assertEqual(record["current_state"], "runnable")

    def test_retry_scheduled_job_skipped_before_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-1")
            registry = FileJobRegistry(output_root / "job_registry.json", now=self._fixed_now)
            registry.upsert(
                {
                    "job_id": "job-1",
                    "current_state": STATE_RETRY_SCHEDULED,
                    "artifact_root": str(artifacts_root / "job-1"),
                    "run_root": str(output_root / "job-1"),
                    "next_eligible_at": "2026-04-18T15:00:00",
                }
            )

            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now, registry=registry)
            summary = scheduler.run_registry_cycle(
                artifacts_root=artifacts_root,
                output_root=output_root,
                max_jobs=5,
            )

        self.assertEqual(summary["jobs_run"], 0)
        self.assertEqual(summary["jobs_skipped_retry_scheduled"], 1)

    def test_registry_cached_next_eligible_does_not_override_active_pause_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-1")
            run_root = output_root / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "pause_state.json").write_text(
                json.dumps(
                    {
                        "pause_schema_version": "v1",
                        "job_id": "job-1",
                        "lifecycle_state": "paused",
                        "pause_state": "waiting_for_checks",
                        "next_eligible_at": "2026-04-18T15:30:00",
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            registry = FileJobRegistry(output_root / "job_registry.json", now=self._fixed_now)
            registry.upsert(
                {
                    "job_id": "job-1",
                    "current_state": STATE_RETRY_SCHEDULED,
                    "artifact_root": str(artifacts_root / "job-1"),
                    "run_root": str(run_root),
                    "next_eligible_at": "2026-04-18T13:00:00",
                }
            )

            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now, registry=registry)
            records = scheduler.sync_registry_from_artifacts(artifacts_root=artifacts_root, output_root=output_root)

        record = next(item for item in records if item["job_id"] == "job-1")
        self.assertEqual(record["current_state"], STATE_PAUSED)
        self.assertEqual(record["next_eligible_at"], "2026-04-18T15:30:00")

    def test_terminal_refusal_not_reclassified_as_retry_scheduled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-1")
            run_root = output_root / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "run_audit.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "job_id": "job-1",
                        "records": [
                            {
                                "job_id": "job-1",
                                "outcome_status": "escalated",
                                "routing_reason": "terminal refusal for failure_type=auth_failure",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            registry = FileJobRegistry(output_root / "job_registry.json", now=self._fixed_now)
            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now, registry=registry)
            records = scheduler.sync_registry_from_artifacts(artifacts_root=artifacts_root, output_root=output_root)

        record = next(item for item in records if item["job_id"] == "job-1")
        self.assertEqual(record["current_state"], STATE_FAILED_TERMINAL)

    def test_escalate_to_human_not_reclassified_as_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-1")
            run_root = output_root / "job-1"
            run_root.mkdir(parents=True, exist_ok=True)
            (run_root / "run_audit.json").write_text(
                json.dumps(
                    {
                        "schema_version": "v1",
                        "job_id": "job-1",
                        "records": [
                            {
                                "job_id": "job-1",
                                "outcome_status": "escalated",
                                "routing_reason": "unsupported_or_non_routable_action",
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
                encoding="utf-8",
            )
            registry = FileJobRegistry(output_root / "job_registry.json", now=self._fixed_now)
            scheduler = JobScheduler(dispatcher=_FakeDispatcher(), now=self._fixed_now, registry=registry)
            records = scheduler.sync_registry_from_artifacts(artifacts_root=artifacts_root, output_root=output_root)

        record = next(item for item in records if item["job_id"] == "job-1")
        self.assertEqual(record["current_state"], STATE_ESCALATED)

    def test_run_registry_cycle_respects_lease_and_updates_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifacts_root = root / "artifacts"
            output_root = root / "executions"
            self._write_planning_dir(artifacts_root, "job-1")
            self._write_planning_dir(artifacts_root, "job-2")
            dispatcher = _FakeDispatcher(
                responses={
                    "job-1": {
                        "job_id": "job-1",
                        "dispatch_status": "executed",
                        "audit": {"routing_reason": "executor_succeeded", "whether_human_required": False},
                    },
                    "job-2": {
                        "job_id": "job-2",
                        "dispatch_status": "escalated",
                        "audit": {"routing_reason": "terminal refusal for failure_type=auth_failure", "whether_human_required": True},
                    },
                }
            )
            scheduler = JobScheduler(dispatcher=dispatcher, now=self._fixed_now)
            summary = scheduler.run_registry_cycle(
                artifacts_root=artifacts_root,
                output_root=output_root,
                holder="test-holder",
                lease_seconds=120,
                max_jobs=10,
            )

            registry = FileJobRegistry(output_root / "job_registry.json", now=self._fixed_now)
            record1 = registry.get("job-1")
            record2 = registry.get("job-2")
            assert record1 is not None
            assert record2 is not None

        self.assertEqual(summary["jobs_run"], 2)
        self.assertEqual(record1["current_state"], "completed")
        self.assertEqual(record2["current_state"], "failed_terminal")

    def test_cli_bounded_one_cycle(self) -> None:
        module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_scheduler_cycle.py"
        spec = importlib.util.spec_from_file_location("run_scheduler_cycle_module", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class _FakeCliScheduler:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def run_registry_cycles(self, **kwargs):
                self.calls.append(kwargs)
                return {
                    "cycle_count": 1,
                    "jobs_considered": 2,
                    "jobs_claimed": 1,
                    "jobs_skipped_paused": 1,
                    "jobs_skipped_leased": 0,
                    "jobs_run": 1,
                    "jobs_resumed": 0,
                    "jobs_paused": 0,
                    "jobs_escalated": 0,
                    "jobs_completed": 1,
                }

        fake_scheduler = _FakeCliScheduler()
        original_builder = module.build_scheduler
        try:
            module.build_scheduler = lambda **kwargs: fake_scheduler
            with tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                artifacts_root = root / "artifacts"
                artifacts_root.mkdir(parents=True, exist_ok=True)
                output_root = root / "executions"
                exit_code = module.main(
                    [
                        "--artifacts-root",
                        str(artifacts_root),
                        "--output-root",
                        str(output_root),
                        "--max-cycles",
                        "1",
                        "--max-jobs",
                        "5",
                        "--json",
                    ]
                )
        finally:
            module.build_scheduler = original_builder

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(fake_scheduler.calls), 1)
        self.assertEqual(fake_scheduler.calls[0]["max_cycles"], 1)

    def test_cli_bounded_multi_cycle_without_daemonization(self) -> None:
        module_path = Path(__file__).resolve().parents[1] / "scripts" / "run_scheduler_cycle.py"
        spec = importlib.util.spec_from_file_location("run_scheduler_cycle_module", module_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class _FakeCliScheduler:
            def __init__(self) -> None:
                self.calls: list[dict[str, object]] = []

            def run_registry_cycles(self, **kwargs):
                self.calls.append(kwargs)
                return {"cycle_count": int(kwargs.get("max_cycles", 0)), "jobs_considered": 0}

        fake_scheduler = _FakeCliScheduler()
        original_builder = module.build_scheduler
        try:
            module.build_scheduler = lambda **kwargs: fake_scheduler
            with tempfile.TemporaryDirectory() as tmp_dir:
                root = Path(tmp_dir)
                artifacts_root = root / "artifacts"
                artifacts_root.mkdir(parents=True, exist_ok=True)
                output_root = root / "executions"
                exit_code = module.main(
                    [
                        "--artifacts-root",
                        str(artifacts_root),
                        "--output-root",
                        str(output_root),
                        "--max-cycles",
                        "3",
                        "--max-jobs",
                        "2",
                        "--json",
                    ]
                )
        finally:
            module.build_scheduler = original_builder

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(fake_scheduler.calls), 1)
        self.assertEqual(fake_scheduler.calls[0]["max_cycles"], 3)


if __name__ == "__main__":
    unittest.main()

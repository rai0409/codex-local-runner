from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from automation.execution.codex_executor_adapter import CodexExecutorAdapter
from automation.execution.codex_executor_adapter import normalize_result_json
from automation.execution.codex_executor_adapter import select_execution_transport
from orchestrator.job_evaluator import evaluate_job_directory


class _FakeTransport:
    def __init__(self) -> None:
        self.launch_calls: list[dict[str, object]] = []
        self.poll_calls: list[dict[str, object]] = []
        self.collect_calls: list[dict[str, object]] = []

    def launch_job(self, **kwargs):
        self.launch_calls.append(dict(kwargs))
        return {"run_id": "run-1", "status": "running"}

    def poll_status(self, **kwargs):
        self.poll_calls.append(dict(kwargs))
        return {"run_id": kwargs["run_id"], "status": "completed"}

    def collect_artifacts(self, **kwargs):
        self.collect_calls.append(dict(kwargs))
        return {
            "stdout_path": "/tmp/stdout.txt",
            "stderr_path": "/tmp/stderr.txt",
        }


class CodexExecutorAdapterTests(unittest.TestCase):
    def _pr_unit(self) -> dict[str, object]:
        return {
            "pr_id": "proj-compiler-plan-v1-pr-02",
            "title": "[execution] Add adapter normalization",
            "exact_scope": "Add codex executor adapter module and tests",
            "touched_files": [
                "automation/execution/codex_executor_adapter.py",
                "tests/test_codex_executor_adapter.py",
            ],
            "forbidden_files": ["orchestrator/merge_executor.py"],
            "acceptance_criteria": ["Result normalization is conservative"],
            "validation_commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"],
            "rollback_notes": "Revert adapter changes if normalization contract breaks.",
            "tier_category": "runtime_fix_high_risk",
            "depends_on": ["proj-compiler-plan-v1-pr-01"],
        }

    def test_adapter_launch_poll_collect_delegate_to_transport(self) -> None:
        transport = _FakeTransport()
        adapter = CodexExecutorAdapter(transport=transport)

        launch = adapter.launch_job(
            job_id="job-1",
            pr_id="proj-compiler-plan-v1-pr-02",
            prompt_path="/tmp/prompt.md",
            work_dir="/tmp/work",
            metadata={"k": "v"},
        )
        poll = adapter.poll_status(run_id="run-1")
        artifacts = adapter.collect_artifacts(run_id="run-1")

        self.assertEqual(launch["run_id"], "run-1")
        self.assertEqual(poll["status"], "completed")
        self.assertIn("stdout_path", artifacts)
        self.assertEqual(len(transport.launch_calls), 1)
        self.assertEqual(len(transport.poll_calls), 1)
        self.assertEqual(len(transport.collect_calls), 1)

    def test_select_execution_transport_dry_run(self) -> None:
        dry_run_transport = _FakeTransport()
        live_transport = _FakeTransport()
        selected, mode = select_execution_transport(
            mode="dry-run",
            dry_run_transport=dry_run_transport,
            live_transport=live_transport,
            live_transport_enabled=True,
        )
        self.assertIs(selected, dry_run_transport)
        self.assertEqual(mode, "dry-run")

    def test_select_execution_transport_live_requires_gate(self) -> None:
        with self.assertRaises(ValueError):
            select_execution_transport(
                mode="live",
                dry_run_transport=_FakeTransport(),
                live_transport=_FakeTransport(),
                live_transport_enabled=False,
            )

    def test_select_execution_transport_live_selected_when_enabled(self) -> None:
        live_transport = _FakeTransport()
        selected, mode = select_execution_transport(
            mode="live",
            dry_run_transport=_FakeTransport(),
            live_transport=live_transport,
            live_transport_enabled=True,
        )
        self.assertIs(selected, live_transport)
        self.assertEqual(mode, "live")

    def test_select_execution_transport_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            select_execution_transport(
                mode="unexpected",
                dry_run_transport=_FakeTransport(),
                live_transport=_FakeTransport(),
                live_transport_enabled=True,
            )

    def test_result_normalization_successful_execution(self) -> None:
        normalized = normalize_result_json(
            job_id="job-success",
            pr_unit=self._pr_unit(),
            raw_result={
                "status": "completed",
                "attempt_count": 1,
                "started_at": "2026-04-18T00:00:00+00:00",
                "finished_at": "2026-04-18T00:05:00+00:00",
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
                "verify": {
                    "status": "passed",
                    "commands": ["python3 -m unittest tests.test_codex_executor_adapter -v"],
                },
                "changed_files": ["automation/execution/codex_executor_adapter.py"],
                "additions": 42,
                "deletions": 3,
                "generated_patch_summary": "Added executor adapter foundation.",
                "cost": {
                    "tokens_input": 1000,
                    "tokens_output": 450,
                },
            },
        )

        self.assertEqual(normalized["job_id"], "job-success")
        self.assertEqual(normalized["pr_id"], "proj-compiler-plan-v1-pr-02")
        self.assertEqual(normalized["execution"]["status"], "completed")
        self.assertEqual(normalized["execution"]["verify"]["status"], "passed")
        self.assertEqual(normalized["failure_type"], None)
        self.assertEqual(normalized["failure_message"], None)
        self.assertEqual(normalized["cost"]["tokens_input"], 1000)
        self.assertEqual(normalized["cost"]["tokens_output"], 450)

    def test_result_normalization_failed_execution(self) -> None:
        normalized = normalize_result_json(
            job_id="job-failed",
            pr_unit=self._pr_unit(),
            raw_result={
                "status": "failed",
                "attempt_count": 1,
                "stderr_path": "/tmp/stderr.txt",
                "error": "codex process exited with code 2",
                "verify": {
                    "status": "not_run",
                    "commands": [],
                },
                "cost": {
                    "tokens_input": 12,
                    "tokens_output": 0,
                },
            },
        )

        self.assertEqual(normalized["execution"]["status"], "failed")
        self.assertEqual(normalized["execution"]["verify"]["status"], "not_run")
        self.assertEqual(normalized["failure_type"], "execution_failure")
        self.assertIn("codex process exited", normalized["failure_message"])

    def test_result_normalization_when_verify_data_missing(self) -> None:
        normalized = normalize_result_json(
            job_id="job-missing-verify",
            pr_unit=self._pr_unit(),
            raw_result={
                "status": "completed",
                "attempt_count": 1,
                "stdout_path": "/tmp/stdout.txt",
                "stderr_path": "/tmp/stderr.txt",
            },
        )

        self.assertEqual(normalized["execution"]["status"], "completed")
        self.assertEqual(normalized["execution"]["verify"]["status"], "not_run")
        self.assertEqual(
            normalized["execution"]["verify"]["reason"],
            "validation_not_run_verify_data_missing",
        )
        self.assertEqual(normalized["failure_type"], "missing_signal")

    def test_pr_id_mapping_stable_against_raw_mismatch(self) -> None:
        normalized = normalize_result_json(
            job_id="job-pr-map",
            pr_unit=self._pr_unit(),
            raw_result={
                "status": "completed",
                "pr_id": "different-pr-id",
                "verify": {
                    "status": "passed",
                    "commands": [],
                },
            },
        )
        self.assertEqual(normalized["pr_id"], "proj-compiler-plan-v1-pr-02")

    def test_compatibility_with_evaluator_assumptions(self) -> None:
        normalized = normalize_result_json(
            job_id="job-eval-compat",
            pr_unit=self._pr_unit(),
            raw_result={
                "status": "completed",
                "attempt_count": 1,
                "verify": {
                    "status": "passed",
                    "commands": ["echo verify"],
                },
                "changed_files": ["docs/reviewer_runbook.md"],
                "additions": 5,
                "deletions": 1,
            },
        )

        with tempfile.TemporaryDirectory() as job_dir:
            root = Path(job_dir)
            (root / "request.json").write_text(
                '{"job_id":"job-eval-compat","declared_category":"docs_only","changed_files":["docs/reviewer_runbook.md"],"validation_commands":["echo verify"]}',
                encoding="utf-8",
            )
            import json

            (root / "result.json").write_text(
                json.dumps(normalized, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            evaluated = evaluate_job_directory(root)

        self.assertEqual(evaluated["job_id"], "job-eval-compat")
        self.assertTrue(evaluated["rubric"]["required_tests_executed"])
        self.assertTrue(evaluated["rubric"]["required_tests_passed"])


if __name__ == "__main__":
    unittest.main()

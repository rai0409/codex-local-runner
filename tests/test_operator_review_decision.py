from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from orchestrator.ledger import get_rollback_execution_by_job_id
from orchestrator.ledger import get_rollback_execution_by_trace_id
from orchestrator.ledger import get_rollback_trace_by_job_id
from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate


class OperatorReviewDecisionCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "operator_review_decision.py"

    def _load_script_module(self):
        spec = importlib.util.spec_from_file_location("operator_review_decision_script", self._script_path())
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _seed_job(self, *, db_path: Path, job_id: str, repo: str = "codex-local-runner") -> tuple[Path, Path]:
        request_path = db_path.parent / f"{job_id}_request.json"
        result_path = db_path.parent / f"{job_id}_result.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
        result_path.write_text(json.dumps({"job_id": job_id}), encoding="utf-8")
        record_job_evaluation(
            db_path=db_path,
            job_id=job_id,
            repo=repo,
            task_type="orchestration",
            provider="codex_cli",
            accepted_status="accepted",
            declared_category="docs_only",
            observed_category="docs_only",
            merge_eligible=True,
            merge_gate_passed=True,
            created_at="2026-04-13T00:00:00+00:00",
            request_path=str(request_path),
            result_path=str(result_path),
            rubric_path=None,
            merge_gate_path=None,
            classification_path=None,
        )
        return request_path, result_path

    def _seed_eligible_rollback_trace(self, *, db_path: Path, job_id: str) -> str:
        candidate_key = record_execution_target(
            db_path=db_path,
            job_id=job_id,
            repo="codex-local-runner",
            target_ref="refs/heads/main",
            source_sha="a" * 40,
            base_sha="b" * 40,
            created_at="2026-04-13T00:00:00+00:00",
        )
        record_merge_execution_outcome(
            db_path=db_path,
            job_id=job_id,
            repo="codex-local-runner",
            target_ref="refs/heads/main",
            source_sha="a" * 40,
            base_sha="b" * 40,
            execution_status="succeeded",
            executed_at="2026-04-13T00:10:00+00:00",
            pre_merge_sha="b" * 40,
            post_merge_sha="c" * 40,
            merge_result_sha="c" * 40,
            merge_error=None,
        )
        trace = record_rollback_traceability_for_candidate(
            db_path=db_path,
            candidate_idempotency_key=candidate_key,
        )
        return str(trace["rollback_trace_id"])

    def test_keep_decision_records_explicit_keep_without_triggering_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            decision_log_path = root / "state" / "operator_review_decisions.jsonl"
            self._seed_job(db_path=db_path, job_id="job-keep")

            proc = self._run(
                [
                    "--job-id",
                    "job-keep",
                    "--decision",
                    "keep",
                    "--db-path",
                    str(db_path),
                    "--decision-log-path",
                    str(decision_log_path),
                    "--json",
                ]
            )

            outcome = json.loads(proc.stdout)
            lines = decision_log_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(outcome["decision"], "keep")
        self.assertEqual(outcome["decision_status"], "recorded")
        self.assertEqual(outcome["rollback_execution"]["status"], "not_requested")
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["decision"], "keep")
        self.assertIsNone(get_rollback_execution_by_job_id("job-keep", db_path=db_path))

    def test_rollback_decision_calls_existing_constrained_rollback_path(self) -> None:
        module = self._load_script_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            decision_log_path = root / "state" / "operator_review_decisions.jsonl"
            self._seed_job(db_path=db_path, job_id="job-rollback")
            rollback_trace_id = self._seed_eligible_rollback_trace(db_path=db_path, job_id="job-rollback")

            with mock.patch.object(
                module,
                "execute_constrained_rollback",
                return_value={
                    "status": "succeeded",
                    "attempted": True,
                    "attempted_at": "2026-04-13T00:20:00+00:00",
                    "consistency_check_passed": True,
                    "current_head_sha": "c" * 40,
                    "rollback_result_sha": "d" * 40,
                    "error": None,
                },
            ) as rollback_mock:
                outcome = module.apply_operator_decision(
                    decision="rollback",
                    db_path=str(db_path),
                    execution_repo_path="/tmp/repo",
                    decision_log_path=str(decision_log_path),
                    rollback_trace_id=rollback_trace_id,
                )

            persisted = get_rollback_execution_by_trace_id(rollback_trace_id, db_path=db_path)

        rollback_mock.assert_called_once()
        self.assertEqual(outcome["decision_status"], "recorded")
        self.assertEqual(outcome["rollback_execution"]["status"], "succeeded")
        self.assertEqual(outcome["rollback_execution"]["persistence"], "written")
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted["execution_status"], "succeeded")

    def test_rollback_denial_from_consistency_checks_is_preserved_and_visible(self) -> None:
        module = self._load_script_module()
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            decision_log_path = root / "state" / "operator_review_decisions.jsonl"
            self._seed_job(db_path=db_path, job_id="job-denied")
            rollback_trace_id = self._seed_eligible_rollback_trace(db_path=db_path, job_id="job-denied")

            with mock.patch.object(
                module,
                "execute_constrained_rollback",
                return_value={
                    "status": "skipped",
                    "attempted": False,
                    "attempted_at": "2026-04-13T00:20:00+00:00",
                    "consistency_check_passed": False,
                    "current_head_sha": "c" * 40,
                    "rollback_result_sha": None,
                    "error": "current_head_mismatch_post_merge",
                },
            ):
                outcome = module.apply_operator_decision(
                    decision="rollback",
                    db_path=str(db_path),
                    execution_repo_path="/tmp/repo",
                    decision_log_path=str(decision_log_path),
                    rollback_trace_id=rollback_trace_id,
                )

            persisted = get_rollback_execution_by_trace_id(rollback_trace_id, db_path=db_path)

        self.assertEqual(outcome["decision_status"], "recorded")
        self.assertEqual(outcome["rollback_execution"]["status"], "skipped")
        self.assertEqual(outcome["rollback_execution"]["error"], "current_head_mismatch_post_merge")
        self.assertEqual(outcome["rollback_execution"]["persistence"], "written")
        self.assertIsNotNone(persisted)
        assert persisted is not None
        self.assertEqual(persisted["execution_status"], "skipped")
        self.assertEqual(persisted["rollback_error"], "current_head_mismatch_post_merge")

    def test_decision_flow_does_not_depend_on_notifier_delivery_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            decision_log_path = root / "state" / "operator_review_decisions.jsonl"
            notification_log_path = root / "state" / "operator_summary_notifications.jsonl"
            self._seed_job(db_path=db_path, job_id="job-no-notifier")
            self.assertFalse(notification_log_path.exists())

            proc = self._run(
                [
                    "--job-id",
                    "job-no-notifier",
                    "--decision",
                    "keep",
                    "--db-path",
                    str(db_path),
                    "--decision-log-path",
                    str(decision_log_path),
                    "--json",
                ]
            )

            outcome = json.loads(proc.stdout)

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(outcome["decision_status"], "recorded")
        self.assertEqual(outcome["decision"], "keep")

    def test_cli_errors_when_decision_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-arg-error")

            proc = self._run([
                "--job-id",
                "job-arg-error",
                "--db-path",
                str(db_path),
            ])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--decision", proc.stderr)

    def test_cli_errors_when_target_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            proc = self._run([
                "--decision",
                "keep",
                "--db-path",
                str(db_path),
            ])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("one of the arguments --job-id --rollback-trace-id is required", proc.stderr)

    def test_cli_errors_when_both_job_and_trace_are_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-both")
            rollback_trace_id = self._seed_eligible_rollback_trace(db_path=db_path, job_id="job-both")

            proc = self._run([
                "--job-id",
                "job-both",
                "--rollback-trace-id",
                rollback_trace_id,
                "--decision",
                "rollback",
                "--db-path",
                str(db_path),
            ])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not allowed with argument", proc.stderr)

    def test_no_automatic_decision_behavior_is_introduced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-explicit")
            trace = get_rollback_trace_by_job_id("job-explicit", db_path=db_path)

        self.assertIsNone(trace)

    def test_help_text_clarifies_primary_job_id_flow(self) -> None:
        proc = self._run(["--help"])

        self.assertEqual(proc.returncode, 0)
        self.assertIn("Primary flow (recommended)", proc.stdout)
        self.assertIn("--job-id", proc.stdout)
        self.assertIn("Advanced direct-trace flow", proc.stdout)

    def test_human_output_clarifies_keep_is_non_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            decision_log_path = root / "state" / "operator_review_decisions.jsonl"
            self._seed_job(db_path=db_path, job_id="job-keep-human")
            proc = self._run(
                [
                    "--job-id",
                    "job-keep-human",
                    "--decision",
                    "keep",
                    "--db-path",
                    str(db_path),
                    "--decision-log-path",
                    str(decision_log_path),
                ]
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("target_mode: job_id", proc.stdout)
        self.assertIn("decision_effect: bookkeeping_only_no_execution", proc.stdout)
        self.assertIn("rollback_status: not_requested", proc.stdout)
        self.assertIn("rollback_attempted: False", proc.stdout)


if __name__ == "__main__":
    unittest.main()

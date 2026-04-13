from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from orchestrator.ledger import build_candidate_idempotency_key
from orchestrator.ledger import build_merge_attempt_identity_key
from orchestrator.ledger import build_merge_receipt_id
from orchestrator.ledger import get_execution_target_by_identity
from orchestrator.ledger import get_merge_execution_by_candidate_idempotency_key
from orchestrator.ledger import get_rollback_execution_by_job_id
from orchestrator.ledger import get_rollback_execution_by_trace_id
from orchestrator.ledger import get_rollback_trace_by_id
from orchestrator.ledger import get_rollback_trace_by_job_id
from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_merge_attempt_receipt
from orchestrator.ledger import record_rollback_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate


class LedgerTests(unittest.TestCase):
    def _fetch_one(self, db_path: Path, job_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

    def _fetch_execution_target(self, db_path: Path, key: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM execution_targets WHERE candidate_idempotency_key = ?",
                (key,),
            ).fetchone()

    def _fetch_merge_receipt(self, db_path: Path, receipt_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM merge_receipts WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()

    def _fetch_merge_execution(self, db_path: Path, key: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM merge_executions WHERE candidate_idempotency_key = ?",
                (key,),
            ).fetchone()

    def _fetch_rollback_trace(self, db_path: Path, key: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM rollback_traces WHERE candidate_idempotency_key = ?",
                (key,),
            ).fetchone()

    def _fetch_rollback_execution(self, db_path: Path, trace_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute(
                "SELECT * FROM rollback_executions WHERE rollback_trace_id = ?",
                (trace_id,),
            ).fetchone()

    def test_ledger_database_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            record_job_evaluation(
                db_path=db_path,
                job_id="job-db-create",
                repo="codex-local-runner",
                task_type="orchestration",
                provider="codex_cli",
                accepted_status="accepted",
                declared_category="feature",
                observed_category="feature",
                merge_eligible=False,
                merge_gate_passed=False,
                created_at=None,
                request_path="/tmp/request.json",
                result_path="/tmp/result.json",
                rubric_path=None,
                merge_gate_path=None,
            )

            self.assertTrue(db_path.exists())
            row = self._fetch_one(db_path, "job-db-create")
            assert row is not None
            self.assertEqual(row["job_id"], "job-db-create")

    def test_insert_one_accepted_job_row_with_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            request_path = Path(tmp_dir) / "job" / "request.json"
            result_path = Path(tmp_dir) / "job" / "result.json"
            rubric_path = Path(tmp_dir) / "job" / "rubric.json"
            merge_gate_path = Path(tmp_dir) / "job" / "merge_gate.json"
            request_path.parent.mkdir(parents=True, exist_ok=True)
            request_path.write_text("{}", encoding="utf-8")
            result_path.write_text("{}", encoding="utf-8")
            rubric_path.write_text("{}", encoding="utf-8")
            merge_gate_path.write_text("{}", encoding="utf-8")

            record_job_evaluation(
                db_path=db_path,
                job_id="job-accepted",
                repo="codex-local-runner",
                task_type="orchestration",
                provider="codex_cli",
                accepted_status="accepted",
                declared_category="docs_only",
                observed_category="docs_only",
                merge_eligible=True,
                merge_gate_passed=True,
                created_at="2026-04-12T00:00:00+00:00",
                request_path=str(request_path),
                result_path=str(result_path),
                rubric_path=str(rubric_path),
                merge_gate_path=str(merge_gate_path),
                classification_path=None,
            )

            row = self._fetch_one(db_path, "job-accepted")
            assert row is not None
            self.assertEqual(row["repo"], "codex-local-runner")
            self.assertEqual(row["accepted_status"], "accepted")
            self.assertEqual(row["request_path"], str(request_path))
            self.assertEqual(row["result_path"], str(result_path))
            self.assertEqual(row["rubric_path"], str(rubric_path))
            self.assertEqual(row["merge_gate_path"], str(merge_gate_path))
            self.assertIsNone(row["classification_path"])

    def test_re_recording_same_job_id_is_safe_upsert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            record_job_evaluation(
                db_path=db_path,
                job_id="job-upsert",
                repo="codex-local-runner",
                task_type="orchestration",
                provider="codex_cli",
                accepted_status="accepted",
                declared_category="feature",
                observed_category="feature",
                merge_eligible=False,
                merge_gate_passed=False,
                created_at=None,
                request_path="/tmp/job/request.json",
                result_path="/tmp/job/result.json",
                rubric_path=None,
                merge_gate_path=None,
            )
            record_job_evaluation(
                db_path=db_path,
                job_id="job-upsert",
                repo="codex-local-runner",
                task_type="orchestration",
                provider="codex_cli",
                accepted_status="accepted",
                declared_category="docs_only",
                observed_category="docs_only",
                merge_eligible=True,
                merge_gate_passed=True,
                created_at="2026-04-12T00:00:00+00:00",
                request_path="/tmp/job/request.json",
                result_path="/tmp/job/result.json",
                rubric_path="/tmp/job/rubric.json",
                merge_gate_path="/tmp/job/merge_gate.json",
            )

            row = self._fetch_one(db_path, "job-upsert")
            assert row is not None
            self.assertEqual(row["declared_category"], "docs_only")
            self.assertEqual(row["observed_category"], "docs_only")
            self.assertEqual(row["merge_eligible"], 1)
            self.assertEqual(row["merge_gate_passed"], 1)
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE job_id = ?",
                    ("job-upsert",),
                ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_missing_artifact_paths_are_stored_as_null(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            record_job_evaluation(
                db_path=db_path,
                job_id="job-null-paths",
                repo="codex-local-runner",
                task_type="orchestration",
                provider="codex_cli",
                accepted_status="accepted",
                declared_category="feature",
                observed_category="feature",
                merge_eligible=False,
                merge_gate_passed=False,
                created_at=None,
                request_path="/tmp/job/request.json",
                result_path="/tmp/job/result.json",
                rubric_path=None,
                merge_gate_path=None,
                classification_path=None,
            )

            row = self._fetch_one(db_path, "job-null-paths")
            assert row is not None
            self.assertIsNone(row["rubric_path"])
            self.assertIsNone(row["merge_gate_path"])
            self.assertIsNone(row["classification_path"])

    def test_execution_target_capture_persists_identity_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            key = record_execution_target(
                db_path=db_path,
                job_id="job-candidate-1",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
                declared_category="docs_only",
                observed_category="docs_only",
                accepted_status="accepted",
                merge_gate_passed=True,
            )

            row = self._fetch_execution_target(db_path, key)

        assert row is not None
        self.assertEqual(row["job_id"], "job-candidate-1")
        self.assertEqual(row["repo"], "codex-local-runner")
        self.assertEqual(row["target_ref"], "refs/heads/main")
        self.assertEqual(row["source_sha"], "a" * 40)
        self.assertEqual(row["base_sha"], "b" * 40)
        self.assertEqual(row["merge_gate_passed"], 1)

    def test_execution_target_capture_is_idempotent_for_same_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            key = build_candidate_idempotency_key(
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
            )
            key_first = record_execution_target(
                db_path=db_path,
                job_id="job-candidate-old",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
                declared_category="docs_only",
                observed_category="docs_only",
                accepted_status="accepted",
                merge_gate_passed=True,
            )
            key_second = record_execution_target(
                db_path=db_path,
                job_id="job-candidate-new",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T01:00:00+00:00",
                declared_category="docs_only",
                observed_category="docs_only",
                accepted_status="accepted",
                merge_gate_passed=True,
            )

            row = self._fetch_execution_target(db_path, key)
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute(
                    "SELECT COUNT(*) FROM execution_targets WHERE candidate_idempotency_key = ?",
                    (key,),
                ).fetchone()[0]

        self.assertEqual(key, key_first)
        self.assertEqual(key, key_second)
        assert row is not None
        self.assertEqual(row["job_id"], "job-candidate-new")
        self.assertEqual(count, 1)

    def test_merge_receipt_persistence_with_execution_target_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-candidate-1",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
                declared_category="docs_only",
                observed_category="docs_only",
                accepted_status="accepted",
                merge_gate_passed=True,
            )
            receipt_id = record_merge_attempt_receipt(
                db_path=db_path,
                job_id="job-candidate-1",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                merge_attempt_status="failed",
                merge_attempted_at="2026-04-13T00:05:00+00:00",
                merge_result_sha=None,
                merge_error="simulated conflict",
            )
            row = self._fetch_merge_receipt(db_path, receipt_id)

        assert row is not None
        self.assertEqual(row["receipt_id"], receipt_id)
        self.assertEqual(row["job_id"], "job-candidate-1")
        self.assertEqual(row["candidate_idempotency_key"], candidate_key)
        self.assertEqual(row["merge_attempt_status"], "failed")
        self.assertEqual(row["merge_attempted_at"], "2026-04-13T00:05:00+00:00")
        self.assertIsNone(row["merge_result_sha"])
        self.assertEqual(row["merge_error"], "simulated conflict")

    def test_merge_receipt_persistence_is_idempotent_for_same_attempt_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-candidate-old",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
                declared_category="docs_only",
                observed_category="docs_only",
                accepted_status="accepted",
                merge_gate_passed=True,
            )
            receipt_id_first = record_merge_attempt_receipt(
                db_path=db_path,
                job_id="job-candidate-old",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                merge_attempt_status="attempted",
                merge_attempted_at="2026-04-13T00:10:00+00:00",
                merge_result_sha=None,
                merge_error=None,
            )
            receipt_id_second = record_merge_attempt_receipt(
                db_path=db_path,
                job_id="job-candidate-new",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                merge_attempt_status="attempted",
                merge_attempted_at="2026-04-13T00:10:00+00:00",
                merge_result_sha=None,
                merge_error=None,
            )
            row = self._fetch_merge_receipt(db_path, receipt_id_first)
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM merge_receipts").fetchone()[0]
            expected_attempt_key = build_merge_attempt_identity_key(
                candidate_idempotency_key=candidate_key,
                merge_attempt_status="attempted",
                merge_attempted_at="2026-04-13T00:10:00+00:00",
                merge_result_sha=None,
                merge_error=None,
            )

        self.assertEqual(receipt_id_first, receipt_id_second)
        self.assertEqual(
            receipt_id_first,
            build_merge_receipt_id(attempt_identity_key=expected_attempt_key),
        )
        assert row is not None
        self.assertEqual(row["candidate_idempotency_key"], candidate_key)
        self.assertEqual(row["job_id"], "job-candidate-new")
        self.assertEqual(count, 1)

    def test_merge_receipt_persistence_requires_execution_target_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            with self.assertRaises(ValueError):
                record_merge_attempt_receipt(
                    db_path=db_path,
                    job_id="job-no-link",
                    repo="codex-local-runner",
                    target_ref="refs/heads/main",
                    source_sha="a" * 40,
                    base_sha="b" * 40,
                    merge_attempt_status="failed",
                    merge_attempted_at="2026-04-13T00:05:00+00:00",
                    merge_result_sha=None,
                    merge_error="simulated conflict",
                )

    def test_merge_execution_outcome_persistence_with_pre_post_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            key = record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-merge-exec",
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
            row = self._fetch_merge_execution(db_path, key)

        assert row is not None
        self.assertEqual(row["execution_status"], "succeeded")
        self.assertEqual(row["pre_merge_sha"], "b" * 40)
        self.assertEqual(row["post_merge_sha"], "c" * 40)
        self.assertEqual(row["merge_result_sha"], "c" * 40)
        self.assertIsNone(row["merge_error"])

    def test_merge_execution_outcome_upsert_is_idempotent_by_candidate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            key_first = record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-merge-exec-1",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="failed",
                executed_at="2026-04-13T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="b" * 40,
                merge_result_sha=None,
                merge_error="merge conflict",
            )
            key_second = record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-merge-exec-2",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-13T00:11:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
                merge_result_sha="c" * 40,
                merge_error=None,
            )
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM merge_executions").fetchone()[0]
            row = self._fetch_merge_execution(db_path, key_first)

        self.assertEqual(key_first, key_second)
        self.assertEqual(count, 1)
        assert row is not None
        self.assertEqual(row["job_id"], "job-merge-exec-2")
        self.assertEqual(row["execution_status"], "succeeded")
        self.assertEqual(row["post_merge_sha"], "c" * 40)

    def test_rollback_trace_creation_is_eligible_for_successful_merge_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-eligible",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-eligible",
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
            receipt_id = record_merge_attempt_receipt(
                db_path=db_path,
                job_id="job-rollback-eligible",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                merge_attempt_status="succeeded",
                merge_attempted_at="2026-04-13T00:10:00+00:00",
                merge_result_sha="c" * 40,
                merge_error=None,
            )

            row = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                merge_receipt_id=receipt_id,
                db_path=db_path,
            )
            stored = self._fetch_rollback_trace(db_path, candidate_key)

        assert stored is not None
        self.assertEqual(row["candidate_idempotency_key"], candidate_key)
        self.assertEqual(stored["rollback_eligible"], 1)
        self.assertIsNone(stored["ineligible_reason"])
        self.assertEqual(stored["pre_merge_sha"], "b" * 40)
        self.assertEqual(stored["post_merge_sha"], "c" * 40)
        self.assertEqual(stored["merge_receipt_id"], receipt_id)

    def test_rollback_trace_excludes_failed_or_skipped_execution_from_eligibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-ineligible",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-ineligible",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="failed",
                executed_at="2026-04-13T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="b" * 40,
                merge_result_sha=None,
                merge_error="merge conflict",
            )

            row = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )

        self.assertEqual(row["rollback_eligible"], 0)
        self.assertEqual(row["ineligible_reason"], "merge_execution_not_succeeded")

    def test_rollback_trace_is_ineligible_when_success_linkage_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-incomplete",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-incomplete",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-13T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha=None,
                merge_result_sha=None,
                merge_error=None,
            )

            row = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )

        self.assertEqual(row["rollback_eligible"], 0)
        self.assertEqual(row["ineligible_reason"], "merge_execution_linkage_incomplete")

    def test_rollback_trace_persistence_requires_merge_execution_facts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-no-merge",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_attempt_receipt(
                db_path=db_path,
                job_id="job-rollback-no-merge",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                merge_attempt_status="succeeded",
                merge_attempted_at="2026-04-13T00:10:00+00:00",
                merge_result_sha="c" * 40,
                merge_error=None,
            )

            with self.assertRaises(ValueError):
                record_rollback_traceability_for_candidate(
                    candidate_idempotency_key=candidate_key,
                    db_path=db_path,
                )

    def test_get_rollback_trace_by_job_id_returns_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-read",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-read",
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
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )

            row = get_rollback_trace_by_job_id("job-rollback-read", db_path=db_path)

        assert row is not None
        self.assertEqual(row["candidate_idempotency_key"], candidate_key)
        self.assertEqual(row["rollback_eligible"], 1)

    def test_record_rollback_execution_outcome_persists_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-exec",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-exec",
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
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            trace_id = str(trace["rollback_trace_id"])

            first = record_rollback_execution_outcome(
                rollback_trace_id=trace_id,
                execution_status="failed",
                attempted_at="2026-04-13T00:11:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha=None,
                rollback_error="conflict",
                consistency_check_passed=True,
                db_path=db_path,
            )
            second = record_rollback_execution_outcome(
                rollback_trace_id=trace_id,
                execution_status="succeeded",
                attempted_at="2026-04-13T00:12:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha="d" * 40,
                rollback_error=None,
                consistency_check_passed=True,
                db_path=db_path,
            )
            with sqlite3.connect(str(db_path)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM rollback_executions").fetchone()[0]
            row = self._fetch_rollback_execution(db_path, trace_id)

        self.assertEqual(first["rollback_trace_id"], trace_id)
        self.assertEqual(second["rollback_trace_id"], trace_id)
        self.assertEqual(count, 1)
        assert row is not None
        self.assertEqual(row["execution_status"], "succeeded")
        self.assertEqual(row["rollback_result_sha"], "d" * 40)

    def test_record_rollback_execution_outcome_requires_rollback_trace_linkage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            with self.assertRaises(ValueError):
                record_rollback_execution_outcome(
                    rollback_trace_id="missing-trace",
                    execution_status="skipped",
                    attempted_at=None,
                    current_head_sha=None,
                    rollback_result_sha=None,
                    rollback_error="trace not found",
                    consistency_check_passed=False,
                    db_path=db_path,
                )

    def test_get_rollback_trace_by_id_and_execution_accessors_return_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-accessors",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-accessors",
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
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            trace_id = str(trace["rollback_trace_id"])
            record_rollback_execution_outcome(
                rollback_trace_id=trace_id,
                execution_status="skipped",
                attempted_at="2026-04-13T00:12:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha=None,
                rollback_error="already_rolled_back_for_trace",
                consistency_check_passed=True,
                db_path=db_path,
            )

            trace_row = get_rollback_trace_by_id(trace_id, db_path=db_path)
            execution_row = get_rollback_execution_by_trace_id(trace_id, db_path=db_path)
            execution_by_job_row = get_rollback_execution_by_job_id(
                "job-rollback-accessors",
                db_path=db_path,
            )

        assert trace_row is not None
        assert execution_row is not None
        assert execution_by_job_row is not None
        self.assertEqual(trace_row["rollback_trace_id"], trace_id)
        self.assertEqual(execution_row["rollback_trace_id"], trace_id)
        self.assertEqual(execution_by_job_row["rollback_trace_id"], trace_id)

    def test_get_execution_target_by_identity_returns_persisted_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            key = record_execution_target(
                db_path=db_path,
                job_id="job-candidate-read",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            row = get_execution_target_by_identity(
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                db_path=db_path,
            )

        assert row is not None
        self.assertEqual(row["candidate_idempotency_key"], key)

    def test_get_merge_execution_by_candidate_idempotency_key_returns_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.db"
            key = record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-merge-exec-read",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="skipped",
                executed_at="2026-04-13T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="b" * 40,
                merge_result_sha=None,
                merge_error="already_merged_for_candidate",
            )
            row = get_merge_execution_by_candidate_idempotency_key(key, db_path=db_path)

        assert row is not None
        self.assertEqual(row["candidate_idempotency_key"], key)
        self.assertEqual(row["execution_status"], "skipped")


if __name__ == "__main__":
    unittest.main()

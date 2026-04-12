from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from orchestrator.ledger import record_job_evaluation


class LedgerTests(unittest.TestCase):
    def _fetch_one(self, db_path: Path, job_id: str) -> sqlite3.Row | None:
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()

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


if __name__ == "__main__":
    unittest.main()

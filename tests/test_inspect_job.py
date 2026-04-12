from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import record_job_evaluation


class InspectJobCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "inspect_job.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _seed_job(
        self,
        *,
        db_path: Path,
        job_id: str,
        created_at: str | None = "2026-04-12T00:00:00+00:00",
        rubric_path: str | None = None,
        merge_gate_path: str | None = None,
    ) -> None:
        request_path = db_path.parent / f"{job_id}_request.json"
        result_path = db_path.parent / f"{job_id}_result.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text("{}", encoding="utf-8")
        result_path.write_text("{}", encoding="utf-8")
        record_job_evaluation(
            db_path=db_path,
            job_id=job_id,
            repo="codex-local-runner",
            task_type="orchestration",
            provider="codex_cli",
            accepted_status="accepted",
            declared_category="docs_only",
            observed_category="docs_only",
            merge_eligible=True,
            merge_gate_passed=True,
            created_at=created_at,
            request_path=str(request_path),
            result_path=str(result_path),
            rubric_path=rubric_path,
            merge_gate_path=merge_gate_path,
        )

    def test_inspect_by_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-by-id")

            proc = self._run(["--job-id", "job-by-id", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertIn("job_id: job-by-id", proc.stdout)
        self.assertIn("accepted_status: accepted", proc.stdout)
        self.assertIn("request_path:", proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_inspect_latest_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-older",
                created_at="2026-04-11T00:00:00+00:00",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-latest",
                created_at="2026-04-12T00:00:00+00:00",
            )

            proc = self._run(["--latest", "--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertIn("job_id: job-latest", proc.stdout)

    def test_json_output_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-json")

            proc = self._run(["--job-id", "job-json", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["job_id"], "job-json")
        self.assertIn("paths", payload)
        self.assertIn("fail_reasons", payload)
        self.assertIn("rubric", payload["paths"])
        self.assertIn("merge_gate", payload["paths"])

    def test_missing_job_exits_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="known-job")

            proc = self._run(["--job-id", "missing-job", "--db-path", str(db_path)])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Job not found: missing-job", proc.stderr)

    def test_artifact_derived_fail_reasons_are_surfaced_when_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            rubric_path = tmp_root / "rubric.json"
            merge_gate_path = tmp_root / "merge_gate.json"
            rubric_path.write_text(
                json.dumps({"fail_reasons": ["required_tests_not_passed"]}),
                encoding="utf-8",
            )
            merge_gate_path.write_text(
                json.dumps({"fail_reasons": ["category_not_auto_merge_allowed"]}),
                encoding="utf-8",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-fail-reasons",
                rubric_path=str(rubric_path),
                merge_gate_path=str(merge_gate_path),
            )

            proc = self._run(["--job-id", "job-fail-reasons", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["fail_reasons"]["rubric"], ["required_tests_not_passed"])
        self.assertEqual(payload["fail_reasons"]["merge_gate"], ["category_not_auto_merge_allowed"])

    def test_handles_null_or_missing_artifact_paths_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            missing_merge_gate_path = tmp_root / "does_not_exist_merge_gate.json"
            self._seed_job(
                db_path=db_path,
                job_id="job-missing-artifacts",
                rubric_path=None,
                merge_gate_path=str(missing_merge_gate_path),
            )

            proc = self._run(
                [
                    "--job-id",
                    "job-missing-artifacts",
                    "--db-path",
                    str(db_path),
                    "--json",
                ]
            )

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIsNone(payload["paths"]["rubric"])
        self.assertEqual(payload["paths"]["merge_gate"], str(missing_merge_gate_path))
        self.assertEqual(payload["fail_reasons"]["rubric"], [])
        self.assertEqual(payload["fail_reasons"]["merge_gate"], [])

    def test_inspection_does_not_mutate_db_or_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            rubric_path = tmp_root / "rubric.json"
            merge_gate_path = tmp_root / "merge_gate.json"
            rubric_path.write_text(json.dumps({"fail_reasons": ["r1"]}), encoding="utf-8")
            merge_gate_path.write_text(json.dumps({"fail_reasons": ["m1"]}), encoding="utf-8")
            self._seed_job(
                db_path=db_path,
                job_id="job-no-mutate",
                rubric_path=str(rubric_path),
                merge_gate_path=str(merge_gate_path),
            )

            db_before = db_path.read_bytes()
            rubric_before = rubric_path.read_text(encoding="utf-8")
            merge_before = merge_gate_path.read_text(encoding="utf-8")

            proc = self._run(["--job-id", "job-no-mutate", "--db-path", str(db_path), "--json"])

            db_after = db_path.read_bytes()
            rubric_after = rubric_path.read_text(encoding="utf-8")
            merge_after = merge_gate_path.read_text(encoding="utf-8")

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(db_before, db_after)
        self.assertEqual(rubric_before, rubric_after)
        self.assertEqual(merge_before, merge_after)

    def test_usage_error_when_both_job_id_and_latest_are_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-both")
            proc = self._run(
                ["--job-id", "job-both", "--latest", "--db-path", str(db_path)]
            )

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not allowed with argument", proc.stderr)

    def test_usage_error_when_neither_job_id_nor_latest_is_supplied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-neither")
            proc = self._run(["--db-path", str(db_path)])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("one of the arguments --job-id --latest is required", proc.stderr)


if __name__ == "__main__":
    unittest.main()

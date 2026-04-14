from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_machine_review_payload_path
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_rollback_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate


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
        self.assertIn("rollback_trace", payload)
        self.assertIn("rollback_execution", payload)
        self.assertIn("rubric", payload["paths"])
        self.assertIn("merge_gate", payload["paths"])
        self.assertFalse(payload["rollback_trace"]["recorded"])
        self.assertFalse(payload["rollback_execution"]["recorded"])

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

    def test_inspect_surfaces_rollback_traceability_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-rollback-trace")
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-trace",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-12T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-trace",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-12T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
                merge_result_sha="c" * 40,
                merge_error=None,
            )
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )

            proc = self._run(["--job-id", "job-rollback-trace", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["rollback_trace"]["recorded"])
        self.assertTrue(payload["rollback_trace"]["rollback_eligible"])
        self.assertEqual(payload["rollback_trace"]["pre_merge_sha"], "b" * 40)
        self.assertEqual(payload["rollback_trace"]["post_merge_sha"], "c" * 40)

    def test_inspect_surfaces_rollback_execution_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(db_path=db_path, job_id="job-rollback-execution")
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-execution",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-12T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-execution",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                execution_status="succeeded",
                executed_at="2026-04-12T00:10:00+00:00",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
                merge_result_sha="c" * 40,
                merge_error=None,
            )
            trace = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            record_rollback_execution_outcome(
                rollback_trace_id=str(trace["rollback_trace_id"]),
                execution_status="succeeded",
                attempted_at="2026-04-12T00:20:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha="d" * 40,
                rollback_error=None,
                consistency_check_passed=True,
                db_path=db_path,
            )

            proc = self._run(["--job-id", "job-rollback-execution", "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["rollback_execution"]["recorded"])
        self.assertEqual(payload["rollback_execution"]["status"], "succeeded")
        self.assertEqual(payload["rollback_execution"]["rollback_result_sha"], "d" * 40)

    def test_inspect_surfaces_machine_review_recommendation_when_payload_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-machine-review"
            self._seed_job(db_path=db_path, job_id=job_id)
            machine_payload_path = tmp_root / "artifacts" / f"{job_id}_machine_review_payload.json"
            machine_payload_path.parent.mkdir(parents=True, exist_ok=True)
            machine_payload_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "job_id": job_id,
                        "recommended_action": "retry",
                        "policy_version": "deterministic_review_policy.v1",
                        "policy_reasons": ["rollback_execution_failed_retry_candidate"],
                        "requires_human_review": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            record_machine_review_payload_path(
                db_path=db_path,
                job_id=job_id,
                machine_review_payload_path=str(machine_payload_path),
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["machine_review"]["recommended_action"], "retry")
        self.assertEqual(
            payload["machine_review"]["policy_version"],
            "deterministic_review_policy.v1",
        )
        self.assertEqual(
            payload["machine_review"]["policy_reasons"],
            ["rollback_execution_failed_retry_candidate"],
        )
        self.assertTrue(payload["machine_review"]["requires_human_review"])

    def test_inspect_keeps_machine_review_unrecorded_without_ledger_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-machine-review-unrecorded"
            self._seed_job(db_path=db_path, job_id=job_id)
            loose_payload_path = tmp_root / "state" / f"{job_id}_machine_review_payload.json"
            loose_payload_path.write_text(
                json.dumps(
                    {
                        "job_id": job_id,
                        "recommended_action": "keep",
                        "policy_version": "deterministic_review_policy.v1",
                        "policy_reasons": ["validation_passed_and_merge_policy_green"],
                        "requires_human_review": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            proc = self._run(["--job-id", job_id, "--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertIsNone(payload["paths"]["machine_review_payload"])
        self.assertFalse(payload["machine_review"]["recorded"])
        self.assertIsNone(payload["machine_review"]["recommended_action"])
        self.assertIsNone(payload["machine_review"]["policy_version"])
        self.assertEqual(payload["machine_review"]["policy_reasons"], [])
        self.assertIsNone(payload["machine_review"]["requires_human_review"])


if __name__ == "__main__":
    unittest.main()

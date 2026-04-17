from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import get_rollback_execution_by_job_id
from orchestrator.ledger import record_execution_target
from orchestrator.ledger import record_job_evaluation
from orchestrator.ledger import record_merge_execution_outcome
from orchestrator.ledger import record_rollback_execution_outcome
from orchestrator.ledger import record_rollback_traceability_for_candidate


class BuildOperatorSummaryCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "build_operator_summary.py"

    def _inspect_script_path(self) -> Path:
        return self._repo_root() / "scripts" / "inspect_job.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _run_inspect(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._inspect_script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _seed_job(
        self,
        *,
        db_path: Path,
        job_id: str,
        created_at: str,
        verify_status: str | None,
        verify_reason: str | None,
    ) -> tuple[Path, Path]:
        request_path = db_path.parent / f"{job_id}_request.json"
        result_path = db_path.parent / f"{job_id}_result.json"
        request_path.parent.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps({"job_id": job_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        execution = {}
        if verify_status is not None:
            execution = {"verify": {"status": verify_status, "reason": verify_reason}}
        result_path.write_text(
            json.dumps({"job_id": job_id, "execution": execution}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
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
            rubric_path=None,
            merge_gate_path=None,
            classification_path=None,
        )
        return request_path, result_path

    def _seed_candidate_with_merge_execution(
        self,
        *,
        db_path: Path,
        job_id: str,
        execution_status: str,
        pre_merge_sha: str,
        post_merge_sha: str,
    ) -> str:
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
            execution_status=execution_status,
            executed_at="2026-04-13T00:10:00+00:00",
            pre_merge_sha=pre_merge_sha,
            post_merge_sha=post_merge_sha,
            merge_result_sha=post_merge_sha,
            merge_error=None,
        )
        return candidate_key

    def _build_and_read_machine_payload(
        self,
        *,
        db_path: Path,
        job_id: str,
        out_dir: Path,
    ) -> dict[str, object]:
        proc = self._run(
            [
                "--job-id",
                job_id,
                "--db-path",
                str(db_path),
                "--out-dir",
                str(out_dir),
            ]
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload_path = out_dir / f"{job_id}_machine_review_payload.json"
        self.assertTrue(payload_path.exists())
        return json.loads(payload_path.read_text(encoding="utf-8"))

    def test_builds_json_and_html_summary_for_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-summary-1",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            out_dir = tmp_root / "out"

            proc = self._run(
                ["--job-id", "job-summary-1", "--db-path", str(db_path), "--out-dir", str(out_dir)]
            )

            json_path = out_dir / "job-summary-1_operator_summary.json"
            html_path = out_dir / "job-summary-1_operator_summary.html"
            machine_path = out_dir / "job-summary-1_machine_review_payload.json"
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(json_path.exists())
            self.assertTrue(html_path.exists())
            self.assertTrue(machine_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            machine_payload = json.loads(machine_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["job_id"], "job-summary-1")
            self.assertEqual(payload["repo"], "codex-local-runner")
            self.assertEqual(payload["accepted_status"], "accepted")
            self.assertEqual(payload["validation"]["verify_status"], "passed")
            self.assertEqual(payload["merge"]["merge_eligible"], True)
            self.assertEqual(payload["merge"]["merge_gate_passed"], True)
            self.assertIn("request", payload["paths"])
            self.assertIn("result", payload["paths"])
            self.assertEqual(machine_payload["schema_version"], "1.1")
            self.assertEqual(
                machine_payload["action_vocabulary"],
                ["keep", "revise_current_state", "reset_and_retry", "escalate"],
            )

            self.assertEqual(machine_payload["job_id"], "job-summary-1")
            self.assertEqual(machine_payload["repo"], "codex-local-runner")
            self.assertEqual(machine_payload["accepted_status"], "accepted")
            self.assertEqual(machine_payload["merge_eligible"], True)
            self.assertEqual(machine_payload["rollback_eligible"], None)
            self.assertEqual(machine_payload["requires_human_review"], True)
            self.assertEqual(machine_payload["recommended_action"], "escalate")
            self.assertEqual(
                machine_payload["policy_version"],
                "deterministic_review_policy.v2",
            )
            self.assertEqual(
                machine_payload["policy_reasons"],
                ["contract_drift", "insufficient_tests"],
            )
            self.assertIsNone(
                machine_payload["retry_metadata"]["retry_recommended"],
            )
            self.assertEqual(
                machine_payload["retry_metadata"]["retry_basis"],
                [],
            )
            self.assertEqual(
                machine_payload["retry_metadata"]["retry_blockers"],
                [
                    "execution_status_missing",
                    "validation_passed",
                    "required_tests_not_declared",
                    "forbidden_path_signal_missing",
                    "diff_size_signal_missing",
                    "changed_files_missing_or_empty",
                    "runtime_semantics_signal_missing",
                    "contract_shape_signal_missing",
                    "reviewer_fields_signal_missing",
                    "prompt_contract_signal_missing",
                    "blocking_failure_code:contract_drift",
                ],
            )
            self.assertIn("operator_summary_json", machine_payload["artifact_references"])
            self.assertIn("operator_summary_html", machine_payload["artifact_references"])
            self.assertIn("machine_review_payload", machine_payload["artifact_references"])

            html = html_path.read_text(encoding="utf-8")
            self.assertIn('<meta name="viewport" content="width=device-width, initial-scale=1">', html)
            self.assertIn("Operator Summary", html)

    def test_latest_selects_most_recent_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-old",
                created_at="2026-04-12T00:00:00+00:00",
                verify_status="not_run",
                verify_reason="no_validation_commands",
            )
            self._seed_job(
                db_path=db_path,
                job_id="job-new",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            out_dir = tmp_root / "out"
            proc = self._run(["--latest", "--db-path", str(db_path), "--out-dir", str(out_dir)])

            json_path = out_dir / "job-new_operator_summary.json"
            machine_path = out_dir / "job-new_machine_review_payload.json"
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(json_path.exists())
            self.assertTrue(machine_path.exists())
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["job_id"], "job-new")
            self.assertEqual(payload["validation"]["verify_status"], "failed")

    def test_build_syncs_machine_review_reference_for_inspect_with_custom_out_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            job_id = "job-sync-machine-review"
            self._seed_job(
                db_path=db_path,
                job_id=job_id,
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            out_dir = tmp_root / "custom-out"
            expected_machine_payload_path = (
                out_dir / f"{job_id}_machine_review_payload.json"
            ).resolve()

            build_proc = self._run(
                [
                    "--job-id",
                    job_id,
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            inspect_proc = self._run_inspect(
                [
                    "--job-id",
                    job_id,
                    "--db-path",
                    str(db_path),
                    "--json",
                ]
            )
            self.assertEqual(build_proc.returncode, 0, msg=build_proc.stderr)
            self.assertEqual(inspect_proc.returncode, 0, msg=inspect_proc.stderr)
            payload = json.loads(inspect_proc.stdout)
            self.assertTrue(expected_machine_payload_path.exists())
            self.assertEqual(
                payload["paths"]["machine_review_payload"],
                str(expected_machine_payload_path),
            )
            self.assertTrue(payload["machine_review"]["recorded"])
            self.assertEqual(payload["machine_review"]["recommended_action"], "escalate")
            self.assertEqual(
                payload["machine_review"]["policy_version"],
                "deterministic_review_policy.v2",
            )
            self.assertEqual(
                payload["machine_review"]["policy_reasons"],
                ["contract_drift", "insufficient_tests"],
            )
            self.assertTrue(payload["machine_review"]["requires_human_review"])

    def test_missing_job_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-known",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            proc = self._run(["--job-id", "job-missing", "--db-path", str(db_path)])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Job not found: job-missing", proc.stderr)

    def test_summary_includes_rollback_trace_and_execution_status_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-rollback-summary",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="passed",
                verify_reason="all_commands_passed",
            )
            candidate_key = record_execution_target(
                db_path=db_path,
                job_id="job-rollback-summary",
                repo="codex-local-runner",
                target_ref="refs/heads/main",
                source_sha="a" * 40,
                base_sha="b" * 40,
                created_at="2026-04-13T00:00:00+00:00",
            )
            record_merge_execution_outcome(
                db_path=db_path,
                job_id="job-rollback-summary",
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
            record_rollback_execution_outcome(
                db_path=db_path,
                rollback_trace_id=str(trace["rollback_trace_id"]),
                execution_status="succeeded",
                attempted_at="2026-04-13T00:20:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha="d" * 40,
                rollback_error=None,
                consistency_check_passed=True,
            )
            out_dir = tmp_root / "out"
            proc = self._run(
                [
                    "--job-id",
                    "job-rollback-summary",
                    "--db-path",
                    str(db_path),
                    "--out-dir",
                    str(out_dir),
                ]
            )
            payload = json.loads(
                (out_dir / "job-rollback-summary_operator_summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertTrue(payload["rollback"]["trace_recorded"])
        self.assertEqual(payload["rollback"]["rollback_eligible"], True)
        self.assertEqual(payload["rollback"]["rollback_execution_status"], "succeeded")

    def test_machine_policy_recommends_rollback_for_failed_validation_when_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-rollback",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            candidate_key = self._seed_candidate_with_merge_execution(
                db_path=db_path,
                job_id="job-policy-rollback",
                execution_status="succeeded",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
            )
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-rollback",
                out_dir=tmp_root / "out",
            )
            rollback_execution = get_rollback_execution_by_job_id(
                "job-policy-rollback",
                db_path=db_path,
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])
        self.assertIsNone(rollback_execution)

    def test_machine_policy_escalates_when_failed_validation_but_rollback_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-ineligible",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            candidate_key = self._seed_candidate_with_merge_execution(
                db_path=db_path,
                job_id="job-policy-ineligible",
                execution_status="failed",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
            )
            record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-ineligible",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])

    def test_machine_policy_escalates_when_validation_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-not-run",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="not_run",
                verify_reason="no_validation_commands",
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-not-run",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])
        self.assertIsNone(payload["retry_metadata"]["retry_recommended"])
        self.assertEqual(payload["retry_metadata"]["retry_basis"], [])
        self.assertIn(
            "blocking_failure_code:contract_drift",
            payload["retry_metadata"]["retry_blockers"],
        )
        self.assertIn(
            "validation_not_run",
            payload["retry_metadata"]["retry_blockers"],
        )

    def test_machine_policy_escalates_for_unrecognized_validation_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-ambiguous",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="flaky_state",
                verify_reason="unknown_semantics",
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-ambiguous",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])

    def test_machine_policy_recommends_retry_when_prior_rollback_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="job-policy-retry",
                created_at="2026-04-13T00:00:00+00:00",
                verify_status="failed",
                verify_reason="validation_failed",
            )
            candidate_key = self._seed_candidate_with_merge_execution(
                db_path=db_path,
                job_id="job-policy-retry",
                execution_status="succeeded",
                pre_merge_sha="b" * 40,
                post_merge_sha="c" * 40,
            )
            trace = record_rollback_traceability_for_candidate(
                candidate_idempotency_key=candidate_key,
                db_path=db_path,
            )
            record_rollback_execution_outcome(
                db_path=db_path,
                rollback_trace_id=str(trace["rollback_trace_id"]),
                execution_status="failed",
                attempted_at="2026-04-13T00:20:00+00:00",
                current_head_sha="c" * 40,
                rollback_result_sha=None,
                rollback_error="git_revert_conflict",
                consistency_check_passed=True,
            )
            payload = self._build_and_read_machine_payload(
                db_path=db_path,
                job_id="job-policy-retry",
                out_dir=tmp_root / "out",
            )

        self.assertEqual(payload["recommended_action"], "escalate")
        self.assertIn("contract_drift", payload["policy_reasons"])
        self.assertIn("insufficient_tests", payload["policy_reasons"])
        self.assertIsNone(payload["retry_metadata"]["retry_recommended"])
        self.assertEqual(payload["retry_metadata"]["retry_basis"], [])
        self.assertIn(
            "blocking_failure_code:contract_drift",
            payload["retry_metadata"]["retry_blockers"],
        )
        self.assertIn(
            "validation_failed",
            payload["retry_metadata"]["retry_blockers"],
        )


if __name__ == "__main__":
    unittest.main()
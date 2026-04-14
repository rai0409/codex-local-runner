from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import record_job_evaluation


class InspectDecisionHistoryCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "inspect_decision_history.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _seed_job(self, *, db_path: Path, job_id: str) -> Path:
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
            created_at="2026-04-14T00:00:00+00:00",
            request_path=str(request_path),
            result_path=str(result_path),
            rubric_path=None,
            merge_gate_path=None,
            classification_path=None,
        )
        return result_path

    def _write_decision_log(self, path: Path, rows: list[dict[str, object]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def test_filters_by_job_and_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            log_path = root / "state" / "operator_review_decisions.jsonl"
            self._seed_job(db_path=db_path, job_id="job-1")
            self._seed_job(db_path=db_path, job_id="job-2")
            self._write_decision_log(
                log_path,
                [
                    {
                        "decided_at": "2026-04-14T00:00:01+00:00",
                        "decision": "keep",
                        "job_id": "job-1",
                        "decision_status": "recorded",
                        "rollback_execution_status": "not_requested",
                    },
                    {
                        "decided_at": "2026-04-14T00:00:02+00:00",
                        "decision": "rollback",
                        "job_id": "job-1",
                        "decision_status": "recorded",
                        "rollback_execution_status": "succeeded",
                    },
                    {
                        "decided_at": "2026-04-14T00:00:03+00:00",
                        "decision": "retry",
                        "job_id": "job-2",
                        "decision_status": "recorded",
                        "rollback_execution_status": "not_requested",
                    },
                ],
            )

            proc = self._run(
                [
                    "--decision-log-path",
                    str(log_path),
                    "--db-path",
                    str(db_path),
                    "--job-id",
                    "job-1",
                    "--decision",
                    "rollback",
                    "--json",
                ]
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["decisions"][0]["job_id"], "job-1")
        self.assertEqual(payload["decisions"][0]["decision"], "rollback")

    def test_recommendation_is_shown_separately_from_applied_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            log_path = root / "state" / "operator_review_decisions.jsonl"
            result_path = self._seed_job(db_path=db_path, job_id="job-reco")
            machine_payload_path = result_path.parent / "job-reco_machine_review_payload.json"
            machine_payload_path.write_text(
                json.dumps(
                    {
                        "schema_version": "1.0",
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
            self._write_decision_log(
                log_path,
                [
                    {
                        "decided_at": "2026-04-14T00:10:00+00:00",
                        "decision": "rollback",
                        "decision_effect": "rollback_requested_guardrails_apply",
                        "job_id": "job-reco",
                        "decision_status": "recorded",
                        "rollback_execution_status": "failed",
                    }
                ],
            )

            proc = self._run(
                [
                    "--decision-log-path",
                    str(log_path),
                    "--db-path",
                    str(db_path),
                    "--include-recommendation",
                    "--json",
                ]
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["count"], 1)
        row = payload["decisions"][0]
        self.assertEqual(row["decision"], "rollback")
        self.assertEqual(
            row["current_policy_recommendation"]["recommended_action"],
            "keep",
        )

    def test_retry_bookkeeping_display_is_non_executing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            db_path = root / "state" / "jobs.db"
            log_path = root / "state" / "operator_review_decisions.jsonl"
            self._seed_job(db_path=db_path, job_id="job-retry")
            self._write_decision_log(
                log_path,
                [
                    {
                        "decided_at": "2026-04-14T00:20:00+00:00",
                        "decision": "retry",
                        "decision_effect": "bookkeeping_only_retry_requested_no_execution",
                        "job_id": "job-retry",
                        "decision_status": "recorded",
                        "rollback_execution_status": "not_requested",
                    }
                ],
            )

            proc = self._run(
                [
                    "--decision-log-path",
                    str(log_path),
                    "--db-path",
                    str(db_path),
                ]
            )

        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("decision=retry", proc.stdout)
        self.assertIn("decision_effect=bookkeeping_only_retry_requested_no_execution", proc.stdout)
        self.assertIn("execution_meaning=bookkeeping_only_non_executing", proc.stdout)
        self.assertIn("rollback_execution_status=not_requested", proc.stdout)


if __name__ == "__main__":
    unittest.main()

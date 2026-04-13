from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.ledger import record_job_evaluation
from orchestrator.policy_loader import load_merge_gate_policy


class ListMergeCandidatesCliTests(unittest.TestCase):
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _script_path(self) -> Path:
        return self._repo_root() / "scripts" / "list_merge_candidates.py"

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self._script_path()), *args],
            capture_output=True,
            text=True,
            cwd=self._repo_root(),
        )

    def _safe_category(self) -> str:
        policy = load_merge_gate_policy()
        categories = tuple(policy.get("auto_merge_categories", ()))
        self.assertTrue(categories, "merge_gate.auto_merge_categories must not be empty")
        return str(categories[0])

    def _seed_job(
        self,
        *,
        db_path: Path,
        job_id: str,
        observed_category: str,
        merge_gate_passed: bool,
        accepted_status: str = "accepted",
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
            accepted_status=accepted_status,
            declared_category=observed_category,
            observed_category=observed_category,
            merge_eligible=merge_gate_passed,
            merge_gate_passed=merge_gate_passed,
            created_at=created_at,
            request_path=str(request_path),
            result_path=str(result_path),
            rubric_path=rubric_path,
            merge_gate_path=merge_gate_path,
        )

    def test_candidate_listing_from_recorded_state(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="candidate-1",
                observed_category=safe_category,
                merge_gate_passed=True,
            )

            proc = self._run(["--db-path", str(db_path)])

        self.assertEqual(proc.returncode, 0)
        self.assertIn("candidate-1", proc.stdout)
        self.assertIn(f"observed_category={safe_category}", proc.stdout)

    def test_safe_category_filtering_uses_merge_gate_yaml(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="safe-candidate",
                observed_category=safe_category,
                merge_gate_passed=True,
            )
            self._seed_job(
                db_path=db_path,
                job_id="unsafe-candidate",
                observed_category="runtime_fix_high_risk",
                merge_gate_passed=True,
            )

            proc = self._run(["--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        ids = {item["job_id"] for item in payload["candidates"]}
        self.assertIn("safe-candidate", ids)
        self.assertNotIn("unsafe-candidate", ids)

    def test_merge_gate_passed_filtering(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="passed-candidate",
                observed_category=safe_category,
                merge_gate_passed=True,
            )
            self._seed_job(
                db_path=db_path,
                job_id="failed-candidate",
                observed_category=safe_category,
                merge_gate_passed=False,
            )

            proc = self._run(["--db-path", str(db_path), "--json"])

        payload = json.loads(proc.stdout)
        ids = {item["job_id"] for item in payload["candidates"]}
        self.assertIn("passed-candidate", ids)
        self.assertNotIn("failed-candidate", ids)

    def test_accepted_status_filtering(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="accepted-candidate",
                observed_category=safe_category,
                merge_gate_passed=True,
                accepted_status="accepted",
            )
            self._seed_job(
                db_path=db_path,
                job_id="failed-status",
                observed_category=safe_category,
                merge_gate_passed=True,
                accepted_status="failed",
            )

            proc = self._run(["--db-path", str(db_path), "--json"])

        payload = json.loads(proc.stdout)
        ids = {item["job_id"] for item in payload["candidates"]}
        self.assertIn("accepted-candidate", ids)
        self.assertNotIn("failed-status", ids)

    def test_latest_n_behavior(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="candidate-old",
                observed_category=safe_category,
                merge_gate_passed=True,
                created_at="2026-04-10T00:00:00+00:00",
            )
            self._seed_job(
                db_path=db_path,
                job_id="candidate-mid",
                observed_category=safe_category,
                merge_gate_passed=True,
                created_at="2026-04-11T00:00:00+00:00",
            )
            self._seed_job(
                db_path=db_path,
                job_id="candidate-new",
                observed_category=safe_category,
                merge_gate_passed=True,
                created_at="2026-04-12T00:00:00+00:00",
            )

            proc = self._run(["--db-path", str(db_path), "--latest", "2", "--json"])

        payload = json.loads(proc.stdout)
        self.assertEqual([item["job_id"] for item in payload["candidates"]], ["candidate-new", "candidate-mid"])

    def test_json_output_mode(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            self._seed_job(
                db_path=db_path,
                job_id="candidate-json",
                observed_category=safe_category,
                merge_gate_passed=True,
            )

            proc = self._run(["--db-path", str(db_path), "--json"])

        self.assertEqual(proc.returncode, 0)
        payload = json.loads(proc.stdout)
        self.assertEqual(set(payload.keys()), {"candidates"})
        self.assertEqual(payload["candidates"][0]["job_id"], "candidate-json")
        self.assertEqual(
            set(payload["candidates"][0].keys()),
            {"job_id", "repo", "observed_category", "merge_gate_passed", "created_at"},
        )

    def test_empty_candidate_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            proc_human = self._run(["--db-path", str(db_path)])
            proc_json = self._run(["--db-path", str(db_path), "--json"])

        self.assertEqual(proc_human.returncode, 0)
        self.assertIn("No merge candidates found.", proc_human.stdout)
        self.assertEqual(proc_json.returncode, 0)
        self.assertEqual(json.loads(proc_json.stdout), {"candidates": []})

    def test_no_mutation_of_db_or_artifacts(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_path = tmp_root / "state" / "jobs.db"
            artifact_path = tmp_root / "merge_gate.json"
            artifact_path.write_text(json.dumps({"fail_reasons": []}), encoding="utf-8")
            self._seed_job(
                db_path=db_path,
                job_id="candidate-no-mutate",
                observed_category=safe_category,
                merge_gate_passed=True,
                merge_gate_path=str(artifact_path),
            )
            db_before = db_path.read_bytes()
            artifact_before = artifact_path.read_text(encoding="utf-8")

            proc = self._run(["--db-path", str(db_path), "--json"])

            db_after = db_path.read_bytes()
            artifact_after = artifact_path.read_text(encoding="utf-8")

        self.assertEqual(proc.returncode, 0)
        self.assertEqual(db_before, db_after)
        self.assertEqual(artifact_before, artifact_after)

    def test_invalid_latest_usage_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "state" / "jobs.db"
            proc = self._run(["--db-path", str(db_path), "--latest", "0"])

        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--latest must be a positive integer", proc.stderr)

    def test_db_path_override_works_without_changing_filter_semantics(self) -> None:
        safe_category = self._safe_category()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            db_a = tmp_root / "state_a" / "jobs.db"
            db_b = tmp_root / "state_b" / "jobs.db"
            self._seed_job(
                db_path=db_a,
                job_id="candidate-from-a",
                observed_category=safe_category,
                merge_gate_passed=True,
            )
            self._seed_job(
                db_path=db_b,
                job_id="non-candidate-from-b",
                observed_category=safe_category,
                merge_gate_passed=False,
            )

            proc_a = self._run(["--db-path", str(db_a), "--json"])
            proc_b = self._run(["--db-path", str(db_b), "--json"])

        self.assertEqual(proc_a.returncode, 0)
        self.assertEqual(proc_b.returncode, 0)
        self.assertEqual([item["job_id"] for item in json.loads(proc_a.stdout)["candidates"]], ["candidate-from-a"])
        self.assertEqual(json.loads(proc_b.stdout), {"candidates": []})


if __name__ == "__main__":
    unittest.main()

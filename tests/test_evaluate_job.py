from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator.github_backend import LiveReadOnlyGitHubStateBackend
from orchestrator.job_evaluator import evaluate_job_directory
from orchestrator.job_evaluator import persist_evaluation_artifacts


class EvaluateJobTests(unittest.TestCase):
    def _write_job(self, root: str, request_payload: dict, result_payload: dict) -> None:
        job_dir = Path(root)
        (job_dir / "request.json").write_text(
            json.dumps(request_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (job_dir / "result.json").write_text(
            json.dumps(result_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def test_minimal_job_directory_can_be_evaluated(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-1", "validation_commands": ["echo verify"]},
                result_payload={"job_id": "job-1", "execution": {"verify": {"status": "passed"}}},
            )
            result = evaluate_job_directory(job_dir)

        self.assertEqual(result["job_id"], "job-1")
        self.assertIn("classification", result)
        self.assertIn("rubric", result)
        self.assertIn("merge_gate", result)
        self.assertIn("assumptions", result)

    def test_json_mode_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-json", "validation_commands": []},
                result_payload={"job_id": "job-json", "execution": {"verify": {"status": "not_run"}}},
            )
            cli = self._repo_root() / "scripts" / "evaluate_job.py"
            proc = subprocess.run(
                [sys.executable, str(cli), "--job-dir", job_dir, "--json"],
                check=True,
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        payload = json.loads(proc.stdout)
        self.assertEqual(payload["job_id"], "job-json")
        self.assertIn("classification", payload)
        self.assertIn("rubric", payload)
        self.assertIn("merge_gate", payload)
        self.assertIn("assumptions", payload)
        self.assertIn("progression_state", payload["merge_gate"])
        self.assertIn("policy_eligible", payload["merge_gate"])
        self.assertIn("auto_pr_candidate", payload["merge_gate"])
        self.assertIn("lifecycle_state", payload["merge_gate"])
        self.assertIn("progression_fail_reasons", payload["merge_gate"])
        self.assertIn("github_progression", payload["merge_gate"])
        self.assertEqual(payload["merge_gate"]["github_progression"]["mode"], "read_only")
        self.assertFalse(payload["merge_gate"]["github_progression"]["write_actions_allowed"])

    def test_human_readable_mode_output_shape(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-human", "validation_commands": []},
                result_payload={"job_id": "job-human", "execution": {"verify": {"status": "not_run"}}},
            )
            cli = self._repo_root() / "scripts" / "evaluate_job.py"
            proc = subprocess.run(
                [sys.executable, str(cli), "--job-dir", job_dir],
                check=True,
                capture_output=True,
                text=True,
                cwd=self._repo_root(),
            )

        output = proc.stdout
        self.assertIn("Job ID: job-human", output)
        self.assertIn("Declared Category:", output)
        self.assertIn("Observed Category:", output)
        self.assertIn("Merge Eligible:", output)
        self.assertIn("Merge Gate Passed:", output)

    def test_derivation_from_request_validation_commands(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-tests", "validation_commands": ["echo one"]},
                result_payload={"job_id": "job-tests", "execution": {"verify": {"status": "passed"}}},
            )
            result = evaluate_job_directory(job_dir)

        self.assertTrue(result["rubric"]["required_tests_declared"])
        self.assertEqual(result["assumptions"]["required_tests_declared_source"], "request.validation_commands")

    def test_derivation_from_result_execution_verify_status(self) -> None:
        for status, expected_executed, expected_passed in (
            ("passed", True, True),
            ("failed", True, False),
            ("not_run", False, False),
        ):
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as job_dir:
                    self._write_job(
                        job_dir,
                        request_payload={"job_id": f"job-verify-{status}", "validation_commands": ["echo one"]},
                        result_payload={
                            "job_id": f"job-verify-{status}",
                            "execution": {"verify": {"status": status}},
                        },
                    )
                    result = evaluate_job_directory(job_dir)

                self.assertEqual(result["rubric"]["required_tests_executed"], expected_executed)
                self.assertEqual(result["rubric"]["required_tests_passed"], expected_passed)
                self.assertEqual(result["assumptions"]["verify_source"], "result.execution.verify.status")

    def test_exact_fallback_behavior_when_signals_missing(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-fallbacks"},
                result_payload={"job_id": "job-fallbacks", "execution": {}},
            )
            result = evaluate_job_directory(job_dir)

        self.assertEqual(result["classification"]["declared_category"], "feature")
        self.assertEqual(result["assumptions"]["declared_category_source"], "fallback_feature")
        self.assertEqual(result["classification"]["changed_files"], ())
        self.assertEqual(result["assumptions"]["changed_files_source"], "fallback_empty_tuple")
        self.assertFalse(result["rubric"]["required_tests_executed"])
        self.assertFalse(result["rubric"]["required_tests_passed"])
        self.assertEqual(result["assumptions"]["verify_source"], "fallback_no_execution_verify")
        self.assertFalse(result["rubric"]["ci_required_checks_green"])
        self.assertEqual(result["assumptions"]["ci_green_source"], "fallback_false_no_ci_signal")
        self.assertFalse(result["rubric"]["rollback_metadata_recorded"])
        self.assertEqual(
            result["assumptions"]["rollback_metadata_source"],
            "fallback_false_no_rollback_signal",
        )
        self.assertEqual(result["assumptions"]["github_backend"], "artifact_read_only")
        self.assertEqual(result["assumptions"]["github_mode"], "read_only")
        self.assertEqual(result["assumptions"]["github_state_source"], "none")
        self.assertEqual(result["assumptions"]["additions_source"], "fallback_additions_missing")
        self.assertEqual(result["assumptions"]["deletions_source"], "fallback_deletions_missing")
        self.assertIn("fallback_feature", result["assumptions"]["fallbacks_used"])
        self.assertIn("fallback_empty_tuple", result["assumptions"]["fallbacks_used"])
        self.assertIn("github_state_unavailable", result["assumptions"]["fallbacks_used"])
        self.assertIn(
            "diff_line_stats_missing",
            result["merge_gate"]["progression_fail_reasons"],
        )

    def test_evaluation_does_not_mutate_source_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-no-mutate", "validation_commands": []},
                result_payload={"job_id": "job-no-mutate", "execution": {}},
            )
            request_path = Path(job_dir) / "request.json"
            result_path = Path(job_dir) / "result.json"
            request_before = request_path.read_text(encoding="utf-8")
            result_before = result_path.read_text(encoding="utf-8")

            _ = evaluate_job_directory(job_dir)

            request_after = request_path.read_text(encoding="utf-8")
            result_after = result_path.read_text(encoding="utf-8")

        self.assertEqual(request_before, request_after)
        self.assertEqual(result_before, result_after)

    def test_evaluation_is_deterministic_across_repeated_runs(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-repeat", "validation_commands": ["echo one"]},
                result_payload={"job_id": "job-repeat", "execution": {"verify": {"status": "failed"}}},
            )
            first = evaluate_job_directory(job_dir)
            second = evaluate_job_directory(job_dir)

        self.assertEqual(first, second)

    def test_repeated_artifact_generation_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={"job_id": "job-artifacts", "validation_commands": ["echo one"]},
                result_payload={"job_id": "job-artifacts", "execution": {"verify": {"status": "failed"}}},
            )
            first_written = persist_evaluation_artifacts(job_dir)
            rubric_first = (Path(job_dir) / "rubric.json").read_text(encoding="utf-8")
            merge_first = (Path(job_dir) / "merge_gate.json").read_text(encoding="utf-8")

            second_written = persist_evaluation_artifacts(job_dir)
            rubric_second = (Path(job_dir) / "rubric.json").read_text(encoding="utf-8")
            merge_second = (Path(job_dir) / "merge_gate.json").read_text(encoding="utf-8")

        self.assertEqual(first_written, ("rubric.json", "merge_gate.json"))
        self.assertEqual(second_written, ("rubric.json", "merge_gate.json"))
        self.assertEqual(rubric_first, rubric_second)
        self.assertEqual(merge_first, merge_second)

    def test_github_signals_are_emitted_in_merge_gate_output(self) -> None:
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={
                    "job_id": "job-github-signals",
                    "repo": "codex-local-runner",
                    "declared_category": "docs_only",
                    "changed_files": ["docs/reviewer_handoff.md"],
                    "validation_commands": ["echo verify"],
                    "metadata": {
                        "execution_target": {
                            "target_ref": "refs/heads/main",
                            "source_sha": "a" * 40,
                            "base_sha": "b" * 40,
                        }
                    },
                },
                result_payload={
                    "job_id": "job-github-signals",
                    "execution": {"verify": {"status": "passed"}},
                    "github_state": {
                        "repository": "rai0409/codex-local-runner",
                        "required_checks": ["unit", "lint"],
                        "passing_checks": ["lint", "unit"],
                        "review_state": "approved",
                        "required_approvals": 1,
                        "approvals": 1,
                        "mergeability_state": "clean",
                        "is_draft": False,
                        "pr_number": 101,
                    },
                },
            )
            result = evaluate_job_directory(job_dir)

        github_progression = result["merge_gate"]["github_progression"]
        self.assertEqual(github_progression["mode"], "read_only")
        self.assertFalse(github_progression["write_actions_allowed"])
        self.assertEqual(github_progression["target"]["repository"], "rai0409/codex-local-runner")
        self.assertEqual(github_progression["checks"]["state"], "passing")
        self.assertEqual(github_progression["review"]["state"], "approved")
        self.assertEqual(github_progression["mergeability"]["state"], "clean")
        self.assertEqual(github_progression["progression"]["state"], "ready")
        self.assertEqual(result["merge_gate"]["lifecycle_state"], "manual_only")
        self.assertIn("policy_link", github_progression)

    def test_evaluation_can_use_injected_live_read_only_backend(self) -> None:
        backend = LiveReadOnlyGitHubStateBackend(
            fetch_state=lambda **_: {
                "repository": "rai0409/codex-local-runner",
                "target_ref": "refs/heads/main",
                "required_checks": ["unit"],
                "passing_checks": ["unit"],
                "review_state": "approved",
                "mergeability_state": "clean",
                "is_draft": False,
            }
        )
        with tempfile.TemporaryDirectory() as job_dir:
            self._write_job(
                job_dir,
                request_payload={
                    "job_id": "job-live-backend",
                    "repo": "codex-local-runner",
                    "declared_category": "docs_only",
                    "changed_files": ["docs/reviewer_runbook.md"],
                    "validation_commands": ["echo verify"],
                    "metadata": {"execution_target": {"target_ref": "refs/heads/main"}},
                },
                result_payload={"job_id": "job-live-backend", "execution": {"verify": {"status": "passed"}}},
            )
            result = evaluate_job_directory(job_dir, github_state_backend=backend)

        self.assertEqual(result["assumptions"]["github_backend"], "live_read_only")
        self.assertEqual(result["assumptions"]["github_mode"], "read_only")
        github_progression = result["merge_gate"]["github_progression"]
        self.assertEqual(github_progression["backend"], "live_read_only")
        self.assertEqual(github_progression["source"]["kind"], "live_read_only")
        self.assertFalse(github_progression["write_actions_allowed"])
        self.assertEqual(github_progression["progression"]["state"], "ready")
        self.assertEqual(result["merge_gate"]["lifecycle_state"], "manual_only")


if __name__ == "__main__":
    unittest.main()

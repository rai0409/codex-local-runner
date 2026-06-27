from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.responsibility_scope_matrix import (
    BOUNDARY_BEFORE,
    MATRIX_PATH,
    build_responsibility_matrix,
    run_responsibility_scope_matrix,
    verify_prompt671_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class ResponsibilityScopeMatrixTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        required = [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt668_report.json",
            "artifacts/autonomous_runtime/prompt669_report.json",
            "artifacts/autonomous_runtime/prompt670_report.json",
            "artifacts/autonomous_runtime/prompt671_report.json",
            "artifacts/autonomous_runtime/prompt671_summary.md",
            "artifacts/autonomous_runtime/prompt671_goal_aligned_implementation_report.json",
            "artifacts/autonomous_runtime/prompt671_extended_soak_50/soak_marker.json",
            "artifacts/autonomous_runtime/prompt671_extended_soak_50/evidence_summary.json",
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            [
                "git",
                "-c",
                "user.email=t@example.local",
                "-c",
                "user.name=T",
                "commit",
                "-q",
                "-m",
                "fixture",
            ],
            cwd=repo,
            check=True,
        )
        subprocess.run(
            ["git", "tag", "prompt671-extended-operational-soak-50-ticks"],
            cwd=repo,
            check=True,
        )
        return repo

    def test_prompt671_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt671_baseline(repo)
        self.assertTrue(result["prompt671_tag_reachable"])
        self.assertTrue(result["prompt671_report_exists"])
        self.assertTrue(result["prompt671_extended_soak_artifact_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertTrue(result["prompt671_status_success"])
        self.assertTrue(result["capability_boundary_verified"])

    def test_matrix_generation_has_all_required_categories_and_scores(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            matrix = build_responsibility_matrix(repo)
        self.assertTrue(matrix["prompt671_verified"])
        self.assertEqual(matrix["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertEqual(matrix["responsibility_categories_count"], 27)
        self.assertEqual({item["category_id"] for item in matrix["responsibilities"]}, set(range(1, 28)))
        self.assertIn("score_summary", matrix)
        for key in [
            "current_autonomy_infrastructure_score_out_of_100",
            "current_operational_durability_score_out_of_100",
            "current_real_development_responsibility_score_out_of_100",
            "current_release_documentation_score_out_of_100",
        ]:
            self.assertIsInstance(matrix["score_summary"][key], int)

    def test_each_category_has_required_fields_and_evidence_or_missing_proof(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            matrix = build_responsibility_matrix(repo)
        required = {
            "category_id",
            "category_name",
            "status",
            "confidence_score_out_of_100",
            "evidence_source",
            "missing_proof",
            "safe_validation_task",
            "recommended_prompt_id",
            "pass_criteria",
            "safety_notes",
        }
        valid_statuses = {"proven", "partially_proven", "unproven", "out_of_scope_for_safety"}
        for item in matrix["responsibilities"]:
            self.assertTrue(required.issubset(item), msg=item)
            self.assertIn(item["status"], valid_statuses)
            self.assertGreaterEqual(item["confidence_score_out_of_100"], 0)
            self.assertLessEqual(item["confidence_score_out_of_100"], 100)
            self.assertTrue(item["evidence_source"] or item["missing_proof"])

    def test_unproven_and_partial_categories_have_safe_validation_tasks(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            matrix = build_responsibility_matrix(repo)
        forbidden = [
            "git push",
            "open pr",
            "pull request",
            "merge",
            "rm -rf",
            "credential",
            "cookie",
            "browser profile",
            ".env",
            "private session",
        ]
        for item in matrix["responsibilities"]:
            if item["status"] in {"partially_proven", "unproven"}:
                task = item["safe_validation_task"].lower()
                self.assertTrue(task)
                self.assertFalse(any(term in task for term in forbidden), msg=item)

    def test_unsafe_categories_are_out_of_scope_and_no_unsafe_tasks_are_recommended(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            matrix = build_responsibility_matrix(repo)
        by_id = {item["category_id"]: item for item in matrix["responsibilities"]}
        self.assertEqual(by_id[26]["status"], "out_of_scope_for_safety")
        self.assertEqual(by_id[27]["status"], "out_of_scope_for_safety")
        self.assertTrue(matrix["unsafe_tasks_excluded"])

    def test_next_prompt_sequence_and_reports_are_written(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_responsibility_scope_matrix(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime",
                run_id="prompt672-test",
            )
            matrix_path = repo / MATRIX_PATH
            report_path = repo / "artifacts/autonomous_runtime/prompt672_report.json"
            summary_path = repo / "artifacts/autonomous_runtime/prompt672_summary.md"
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "success", msg=result["errors"])
            self.assertTrue(matrix_path.is_file())
            self.assertTrue(report_path.is_file())
            self.assertTrue(summary_path.is_file())
            self.assertTrue(matrix["next_prompt_sequence_created"])
            self.assertGreaterEqual(len(matrix["next_prompt_sequence"]), 6)
            self.assertTrue(result["safe_real_task_plan_created"])
            self.assertTrue(result["reports_written"])


if __name__ == "__main__":
    unittest.main()

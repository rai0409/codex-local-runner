from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.real_task_test_addition_acceptance import (
    BOUNDARY_BEFORE,
    RUN_DIR,
    TEST_ARTIFACT_PATH,
    build_test_addition_task_goal,
    build_test_addition_task_queue,
    run_real_task_test_addition_acceptance,
    verify_prompt673_baseline,
)
from automation.orchestration.planned_runner.responsibility_scope_matrix import (
    build_responsibility_matrix,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TASK_TERMS = (
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
)


class RealTaskTestAdditionAcceptanceTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        required = [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt668_report.json",
            "artifacts/autonomous_runtime/prompt669_report.json",
            "artifacts/autonomous_runtime/prompt670_report.json",
            "artifacts/autonomous_runtime/prompt671_report.json",
            "artifacts/autonomous_runtime/prompt671_extended_soak_50/soak_marker.json",
            "artifacts/autonomous_runtime/prompt672_report.json",
            "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json",
            "artifacts/autonomous_runtime/prompt673_report.json",
            "docs/autonomous_runtime/responsibility_scope_matrix.md",
            "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md",
            TEST_ARTIFACT_PATH,
        ]
        for path in required:
            source = REPO_ROOT / path
            target = repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@example.local", "-c", "user.name=T", "commit", "-q", "-m", "fixture"],
            cwd=repo,
            check=True,
        )
        subprocess.run(["git", "tag", "prompt671-extended-operational-soak-50-ticks"], cwd=repo, check=True)
        subprocess.run(["git", "tag", "prompt673-real-task-documentation-update-acceptance"], cwd=repo, check=True)
        return repo

    def _matrix(self):
        return build_responsibility_matrix(REPO_ROOT)

    def _run(self, repo: Path, goal=None):
        return run_real_task_test_addition_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt674-test",
            test_addition_goal=goal,
        )

    def test_prompt673_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt673_baseline(repo)
        self.assertTrue(result["prompt673_tag_reachable"])
        self.assertTrue(result["prompt673_report_exists"])
        self.assertTrue(result["prompt673_documentation_artifact_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertTrue(result["prompt673_status_success"])
        self.assertTrue(result["capability_boundary_verified"])

    def test_required_real_task_categories_are_present(self):
        matrix = self._matrix()
        by_name = {item["category_name"]: item for item in matrix["responsibilities"]}
        for name in [
            "Documentation generation/update",
            "Test addition",
            "Small code change",
            "Bugfix from failing test",
            "Multi-file minor refactor",
            "README / demo / GitHub public documentation",
        ]:
            self.assertIn(name, by_name)
        self.assertEqual(by_name["Test addition"]["recommended_prompt_id"], "Prompt674")

    def test_unsafe_responsibilities_remain_out_of_scope(self):
        matrix = self._matrix()
        by_id = {item["category_id"]: item for item in matrix["responsibilities"]}
        self.assertEqual(by_id[26]["status"], "out_of_scope_for_safety")
        self.assertEqual(by_id[27]["status"], "out_of_scope_for_safety")
        self.assertEqual(by_id[26]["recommended_prompt_id"], "none")
        self.assertEqual(by_id[27]["recommended_prompt_id"], "none")

    def test_partial_and_unproven_responsibilities_have_safe_validation_tasks(self):
        matrix = self._matrix()
        for item in matrix["responsibilities"]:
            if item["status"] in {"partially_proven", "unproven"}:
                task = item["safe_validation_task"].lower()
                self.assertTrue(task, msg=item)
                self.assertFalse(any(term in task for term in FORBIDDEN_TASK_TERMS), msg=item)

    def test_next_prompt_sequence_covers_real_task_ladder(self):
        matrix = self._matrix()
        prompts = {item["prompt_id"]: item for item in matrix["next_prompt_sequence"]}
        expected = {
            "Prompt673": "documentation_update_real_task_acceptance",
            "Prompt674": "test_addition_real_task_acceptance",
            "Prompt675": "small_code_change_real_task_acceptance",
            "Prompt676": "failing_test_bugfix_real_task_acceptance",
            "Prompt677": "multi_responsibility_queue_real_task_acceptance",
            "Prompt678": "release_documentation_demo_pack",
        }
        self.assertEqual({key: prompts[key]["title"] for key in expected}, expected)

    def test_score_summary_keeps_real_development_and_release_scores(self):
        scores = self._matrix()["score_summary"]
        for key in [
            "current_autonomy_infrastructure_score_out_of_100",
            "current_operational_durability_score_out_of_100",
            "current_real_development_responsibility_score_out_of_100",
            "current_release_documentation_score_out_of_100",
        ]:
            self.assertIn(key, scores)
            self.assertIsInstance(scores[key], int)
        self.assertLess(scores["current_real_development_responsibility_score_out_of_100"], 50)

    def test_matrix_does_not_recommend_unsafe_tasks(self):
        matrix = self._matrix()
        self.assertTrue(matrix["unsafe_tasks_excluded"])
        for item in matrix["responsibilities"]:
            if item["status"] != "out_of_scope_for_safety":
                combined = f"{item['safe_validation_task']} {item['pass_criteria']}".lower()
                self.assertFalse(any(term in combined for term in FORBIDDEN_TASK_TERMS), msg=item)

    def test_test_addition_task_queue_generation_is_bounded(self):
        queue = build_test_addition_task_queue()
        self.assertEqual(len(queue), 6)
        self.assertLessEqual(len(queue), 10)
        self.assertTrue(all(item["local_only"] for item in queue))

    def test_test_addition_acceptance_run_records_evidence(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            validation = json.loads((run_dir / "test_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertTrue(result["test_artifact_created_or_updated"])
        self.assertTrue(result["durable_state_persisted"])
        self.assertTrue(result["durable_queue_persisted"])
        self.assertTrue(result["per_step_evidence_captured"])
        self.assertTrue(validation["responsibility_matrix_behavior_tested"])
        self.assertTrue(validation["unsafe_out_of_scope_behavior_tested"])
        self.assertTrue(validation["next_prompt_sequence_behavior_tested"])

    def test_safe_goal_required_and_unsafe_goal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_test_addition_task_goal(run_id="prompt674-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_test_addition_task_goal")
        self.assertTrue(result["unsafe_test_addition_task_goal_rejected"])

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_real_task_test_addition_acceptance(
                repo_root=repo,
                out_dir=repo / "artifacts/autonomous_runtime/cookies",
                run_id="unsafe-path",
            )
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_artifact_path")
        self.assertTrue(result["unsafe_paths_rejected"])

    def test_core_artifacts_are_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            protected = [
                "artifacts/autonomous_runtime/prompt667_report.json",
                "artifacts/autonomous_runtime/prompt668_report.json",
                "artifacts/autonomous_runtime/prompt669_report.json",
                "artifacts/autonomous_runtime/prompt670_report.json",
                "artifacts/autonomous_runtime/prompt671_report.json",
                "artifacts/autonomous_runtime/prompt672_report.json",
                "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json",
                "artifacts/autonomous_runtime/prompt673_report.json",
                "docs/autonomous_runtime/responsibility_scope_matrix.md",
                "docs/autonomous_runtime/real_task_responsibility_validation_roadmap.md",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672", "prompt673"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)


if __name__ == "__main__":
    unittest.main()

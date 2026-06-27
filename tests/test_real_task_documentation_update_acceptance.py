from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from automation.orchestration.planned_runner.real_task_documentation_update_acceptance import (
    BOUNDARY_BEFORE,
    IMPLEMENTATION_PATH,
    RUN_DIR,
    build_documentation_task_goal,
    build_documentation_task_queue,
    run_real_task_documentation_update_acceptance,
    verify_prompt672_baseline,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class RealTaskDocumentationUpdateAcceptanceTests(unittest.TestCase):
    def _copy_repo(self, tmp: Path) -> Path:
        repo = tmp / "repo"
        repo.mkdir()
        required = [
            "artifacts/autonomous_runtime/prompt667_report.json",
            "artifacts/autonomous_runtime/prompt668_report.json",
            "artifacts/autonomous_runtime/prompt669_report.json",
            "artifacts/autonomous_runtime/prompt670_report.json",
            "artifacts/autonomous_runtime/prompt671_report.json",
            "artifacts/autonomous_runtime/prompt672_report.json",
            "artifacts/autonomous_runtime/prompt672_responsibility_matrix.json",
            "docs/autonomous_runtime/responsibility_scope_matrix.md",
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
        subprocess.run(["git", "tag", "prompt672-responsibility-scope-matrix-real-task-plan"], cwd=repo, check=True)
        return repo

    def _run(self, repo: Path, goal=None):
        return run_real_task_documentation_update_acceptance(
            repo_root=repo,
            out_dir=repo / "artifacts/autonomous_runtime",
            run_id="prompt673-test",
            documentation_goal=goal,
        )

    def test_prompt672_baseline_verification(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = verify_prompt672_baseline(repo)
        self.assertTrue(result["prompt672_tag_reachable"])
        self.assertTrue(result["prompt672_report_exists"])
        self.assertTrue(result["prompt672_matrix_exists"])
        self.assertTrue(result["project_level_autonomy_complete"])
        self.assertTrue(result["prompt672_status_success"])
        self.assertTrue(result["capability_boundary_verified"])

    def test_documentation_queue_generation_is_bounded(self):
        queue = build_documentation_task_queue()
        self.assertEqual(len(queue), 6)
        self.assertLessEqual(len(queue), 10)
        self.assertTrue(all(item["local_only"] for item in queue))

    def test_documentation_update_run_writes_artifacts_and_validates_sections(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = self._run(repo)
            run_dir = repo / RUN_DIR
            roadmap = (repo / IMPLEMENTATION_PATH).read_text(encoding="utf-8")
            validation = json.loads((run_dir / "documentation_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "success", msg=result["errors"])
        self.assertEqual(result["current_capability_boundary_before"], BOUNDARY_BEFORE)
        self.assertTrue(result["documentation_artifact_created_or_updated"])
        self.assertTrue(result["durable_state_persisted"])
        self.assertTrue(result["durable_queue_persisted"])
        self.assertTrue(result["per_step_evidence_captured"])
        self.assertTrue(validation["required_roadmap_sections_verified"])
        self.assertIn("## Prompt667 Through Prompt672 Evidence Summary", roadmap)
        self.assertIn("current_real_development_responsibility_score_out_of_100=38", roadmap)
        self.assertIn("Prompt674: real_task_test_addition_acceptance", roadmap)
        self.assertIn("Prompt678: release_documentation_and_demo_pack", roadmap)
        self.assertIn("private-session file access are out of scope", roadmap)

    def test_safe_goal_required_and_unsafe_goal_rejected(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            goal = build_documentation_task_goal(run_id="prompt673-test")
            goal["goal_text"] = "git push origin main"
            result = self._run(repo, goal=goal)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["stop_reason"], "unsafe_documentation_task_goal")
        self.assertTrue(result["unsafe_documentation_task_goal_rejected"])

    def test_unsafe_path_rejection(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            repo = self._copy_repo(Path(raw))
            result = run_real_task_documentation_update_acceptance(
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
                "docs/autonomous_runtime/responsibility_scope_matrix.md",
            ]
            before = {path: (repo / path).read_bytes() for path in protected}
            result = self._run(repo)
            after = {path: (repo / path).read_bytes() for path in protected}
        self.assertEqual(before, after)
        for prompt in ("prompt667", "prompt668", "prompt669", "prompt670", "prompt671", "prompt672"):
            self.assertTrue(result[f"{prompt}_core_artifacts_preserved"], msg=prompt)


if __name__ == "__main__":
    unittest.main()
